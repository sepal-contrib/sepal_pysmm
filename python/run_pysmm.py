import argparse
import ast
import concurrent
import datetime
import getpass
import itertools
import os
import sys
import time
import ee

from multiprocessing import Process
from pysmm.derive_SM import get_map

from pysmm.GEE_wrappers import GEE_extent
from pysmm.GEE_wrappers import GEE_pt
from pysmm.utils import gdrive


# Get SEPAL user
user = getpass.getuser()

parser = argparse.ArgumentParser()
parser.add_argument('year')
parser.add_argument('month')
parser.add_argument('day')
parser.add_argument('minlo', type=float)
parser.add_argument('minla', type=float)
parser.add_argument('maxlo', type=float)
parser.add_argument('maxla', type=float)
parser.add_argument('out_att_name')
args = parser.parse_args()

def export_map(file_name, gee_interface):
    print(f'Exporting {file_name}.')
    gee_interface.GEE_2_disk(outdir=out_path, name=file_name, timeout=False)

def remove_duplicates(maps, file_sufix):
    args = []
    for map1 in maps:
        file_name = 'SMCmap_' + \
                str(map1.S1_DATE.year) + '_' + \
                str(map1.S1_DATE.month) + '_' + \
                str(map1.S1_DATE.day) + '_' + \
                file_sufix
        args.append([map1, file_name])
    
    # Remove the repeated images
    unique_maps = dict((x[1], x) for x in args).values()

    return unique_maps

def export_sm(image, file_name):
    
    description = 'fileexp_{}'.format(file_name)
    
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

def export_to_sepal(task, file_name, out_path):
    timeout=True
    start = time.time()
    success = 1
    
    while (task.active() == True):
        time.sleep(2)
        if timeout == True and (time.time() - start) > 4800:
            success = 0
            break
    else:
        print('Export completed')
    print(file_name + '.tif')
    print(out_path + file_name + '.tif')
    
    if success == 1:
       # initialise Google Drive
        drive_handler = gdrive()
        print('Downloading files ...')
        print(file_name)
        drive_handler.download_file(file_name + '.tif',
                                    out_path + file_name + '.tif')
        drive_handler.delete_file(file_name + '.tif')
    else:
        file_exp.cancel()

def list_to_int(arg):
    return [int(s) for s in ast.literal_eval(arg)]


minlon = args.minlo
minlat = args.minla
maxlon = args.maxlo
maxlat = args.maxla
year = list_to_int(args.year)
month = list_to_int(args.month)
day = list_to_int(args.day)

    
out_att_name = str(int(args.out_att_name))

# Create a folder to download the pysmm images
out_path = os.path.join(os.path.expanduser('~'),'pysmm_downloads/')
if not os.path.exists(out_path):
    os.makedirs(out_path)

# Download SM maps to GEE

start = time.perf_counter()
file_sufix = "{}_{}".format(user, out_att_name)
    
maps = []
file_names = []
for y, m, d in itertools.product(year, month, day):
    kwargs = {
        'sampling' : 100,
        'tracknr' : None,
        'tempfilter' : True,
        'mask' : 'Globcover',
        'masksnow' : False,
        'overwrite' : True,
        'filename' : file_sufix,
        'year' : y,
        'month' : m,
        'day' : d
    }
    args=(minlon, minlat, maxlon, maxlat, out_path)
    
    maps.append(get_map(*args, **kwargs))

    
finish = time.perf_counter()
print(f'Images created in {round(finish-start,2)} seconds')

start = time.perf_counter()

print('\nPlease wait until the images are processed and downloaded into your SEPAL account...')

# Download maps into SEPAL account

ee.Initialize()
tasks = [export_sm(year, name) for year, name in remove_duplicates(maps, file_sufix)]

for task, file_name in tasks:
    export_to_sepal(task, file_name, out_path)


finish = time.perf_counter()

print(f'Finished in {round(finish-start,2)} seconds')
print(f'The images were downloaded in {out_path} SEPAL path.')
