#!/usr/bin/env python3

import argparse
import ast
import concurrent
import datetime
import getpass
import itertools
import os
import sys
import subprocess
import time
import ee
import geemap

from derive_SM import get_map
from GEE_wrappers import GEE_extent
from GEE_wrappers import GEE_pt
from utils import gdrive

# Get SEPAL user
user = getpass.getuser()

# Create parser arguments
parser = argparse.ArgumentParser()
parser.add_argument('year', help ="List of years to be processed")
parser.add_argument('month', help ="List of months to be processed")
parser.add_argument('day', help ="List of days to be processed")
parser.add_argument('minlon', type=float)
parser.add_argument('minlat', type=float)
parser.add_argument('maxlon', type=float)
parser.add_argument('maxlat', type=float)
parser.add_argument('out_att_name')
args = parser.parse_args()


download_to_sepal = os.path.join(os.path.expanduser('~'),'sepal_pysmm/scripts/download_to_sepal.py')
def export_images(tasks_file_name, out_path):
    download_to_sepal = os.path.join(os.path.expanduser('~'),'sepal_pysmm/scripts/download_to_sepal.py')
    process = subprocess.Popen(['python3',  download_to_sepal,
                                tasks_file_name,
                                out_path
                            ],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, 
                            universal_newlines=True)
    return process


def export_map(file_name, gee_interface):
    print(f'Exporting {file_name}.')
    gee_interface.GEE_2_disk(outdir=out_path, name=file_name, timeout=False)



def export_sm(image, file_name):
    
    description = f'fileexp_{file_name}'
    
    task = ee.batch.Export.image.toDrive(
        image=image.__getattribute__('ESTIMATED_SM'),
        description=description,
        fileNamePrefix=file_name,
        scale=image.sampling,
        region=image.roi.getInfo()['coordinates'],
        maxPixels=1000000000000
    )
    task.start()
    return task, file_name

        
def list_to_int(arg):
    return [int(s) for s in ast.literal_eval(arg)]



single_date = False
start_date = False

if args.year != 'False':
        
    year = list_to_int(args.year)
    month = list_to_int(args.month)
    day = list_to_int(args.day)

    if len(year)<2:
        year, month, day = year[0], month[0], day[0]
        single_date = True

    else:
        start_date = datetime.datetime(year[0], month[0], day[0]).date()
        stop_date = datetime.datetime(year[1], month[1], day[1]).date()
else:
    year, month, day = False, False, False



# Set the sufix and prefix names
aoi_name, selected_feature = ast.literal_eval(args.out_att_name)
file_sufix = f"{user}_{selected_feature}"
selected_feature = str(int(selected_feature))
aoi_name = aoi_name.split('/')[-1]

# Create a folder to download the pysmm images
out_path = os.path.join(os.path.expanduser('~'), 'pysmm_downloads',
                        '0_raw', aoi_name, selected_feature)
if not os.path.exists(out_path):
    os.makedirs(out_path)

# Download SM maps to GEE

start = time.perf_counter()

args=(args.minlon, args.minlat, args.maxlon, args.maxlat, out_path)
kwargs = {
    'sampling' : 100,
    'tracknr' : None,
    'tempfilter' : True,
    'mask' : 'Globcover',
    'masksnow' : False,
    'overwrite' : True,
    'filename' : file_sufix,
    'year' : None,
    'month' : None,
    'day' : None,
    'start_date' : False,
    'stop_date' : False,
}


# To process single date or non row dates.


if single_date:
    print(f'Processing the closest image to {year}-{month}-{day}...')
    kwargs['year']= year
    kwargs['month']=month
    kwargs['day']=day
    maps = get_map(*args, **kwargs)

# To get the the series map in row
else:

    # To get the series map in a specified range
    if start_date:
        print(f'Processing all images available between {start_date} and {stop_date}...')
        kwargs['start_date'] = start_date
        kwargs['stop_date'] = stop_date
        maps = get_map(*args, **kwargs)

    # To retreive the entire series
    else:
        print(f'Processing all available images in the time series...')
        maps = get_map(*args, **kwargs)

finish = time.perf_counter()
print(f'Image(s) created in {round(finish-start,2)} seconds')

start = time.perf_counter()

print('\nPlease wait until the images are processed and downloaded into your SEPAL account...')

ee.Initialize()

tasks_ids_names = []
for image, filename in maps:
    task, filename = export_sm(image, filename)
    tasks_ids_names.append(f"{task.id}, {filename}\n")

tasks_file_name = os.path.join(out_path, 'tasks_and_names.txt')

with open(tasks_file_name, 'w') as tasks_file:
    for item in tasks_ids_names:
        tasks_file.write(f"{item}")
tasks_file.close()


process = export_images(tasks_file_name, out_path)

finish = time.perf_counter()


print(f'Finished in {round(finish-start,2)} seconds')
print(f'The images are being processed into your GEE accound, after finished, check your {out_path} SEPAL folder.')
print(f'You can copy and paste the following command into the bash console to download the images later: \n')
print(f'python3 {download_to_sepal} {tasks_file_name} {out_path}')




