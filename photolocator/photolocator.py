from PIL import Image
from pillow_heif import register_heif_opener
import os
import pandas as pd
import pandas_geojson as pdg
import ast
import sys

__all__ = ['locate_photos']

def get_exif(filename):
    image = Image.open(filename)
    image.verify()
    return image.getexif().get_ifd(0x8825)

def get_geotagging(exif):
    geo_tagging_info = {}
    if not exif:
        raise ValueError("No EXIF metadata found")
    else:
        gps_keys = ['GPSVersionID', 'GPSLatitudeRef', 'GPSLatitude', 'GPSLongitudeRef', 'GPSLongitude',
                    'GPSAltitudeRef', 'GPSAltitude', 'GPSTimeStamp', 'GPSSatellites', 'GPSStatus', 'GPSMeasureMode',
                    'GPSDOP', 'GPSSpeedRef', 'GPSSpeed', 'GPSTrackRef', 'GPSTrack', 'GPSImgDirectionRef',
                    'GPSImgDirection', 'GPSMapDatum', 'GPSDestLatitudeRef', 'GPSDestLatitude', 'GPSDestLongitudeRef',
                    'GPSDestLongitude', 'GPSDestBearingRef', 'GPSDestBearing', 'GPSDestDistanceRef', 'GPSDestDistance',
                    'GPSProcessingMethod', 'GPSAreaInformation', 'GPSDateStamp', 'GPSDifferential']

        for k, v in exif.items():
            try:
                geo_tagging_info[gps_keys[k]] = str(v)
            except IndexError:
                pass
        return geo_tagging_info

def listdir_nohidden(path):
    for file in os.listdir(path):
        if not file.startswith('.'):
            yield file

def n_coord(coord_string,n=2):
    ls_form = coord_string.split(',')
    result = ls_form[n]
    result = result.replace(')','')
    result = result.replace('(','')
    result = result.replace(' ','')
    return result

def make_n_coord(n):
    def result_func(coord_string):
        return n_coord(coord_string,n)
    return result_func

def convert_from_dms(dms_coords,direction):
    deg, minutes, seconds = dms_coords.split(',')
    deg = float(deg.replace('(','').replace(')','').replace(' ',''))
    minutes = float(minutes.replace('(','').replace(')','').replace(' ',''))
    seconds = float(seconds.replace('(','').replace(')','').replace(' ',''))
    return (float(deg) + float(minutes)/60 + float(seconds)/(60*60)) * (-1 if direction in ['W', 'S'] else 1)

def locate_photos(target_directory, outpath=None):
    results = []

    if target_directory[-1] != '/':
        target_directory += '/'

    register_heif_opener()

    all_images = list(listdir_nohidden(target_directory))[0:90]
    all_image_refs = [target_directory + image for image in all_images]

    for i in range(0,len(all_images)):
        image_ref = all_image_refs[i]
        image_name = all_images[i]

        image_info = get_exif(image_ref)
        image_info = get_geotagging(image_info)
        image_info['File_Name'] = image_name

        results.append(image_info)

    df = pd.DataFrame.from_dict(results)

    df['type'] = 'Point'
    df['coordinates'] = '[' + df['GPSLongitude'].apply(convert_from_dms,args=('W')).apply(str) + ', ' + df['GPSLatitude'].apply(convert_from_dms,args=('N')).apply(str) + ']'
    df['coordinates'] = df['coordinates'].apply(ast.literal_eval)
    df['name'] = df['File_Name'].str.replace('.HEIC','')

    geojson = pdg.GeoJSON.from_dataframe(df,
                                        geometry_type_col='type',
                                        coordinate_col='coordinates',
                                        property_col_list=['name','GPSDateStamp']
                                        )

    if outpath is not None:
        pdg.save_geojson(geojson, outpath, indent=4)
        return True
    else:
        return geojson
