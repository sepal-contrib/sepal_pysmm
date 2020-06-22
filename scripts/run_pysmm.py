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

from .derive_SM import get_map
from .GEE_wrappers import GEE_extent
from .GEE_wrappers import GEE_pt
from .utils import gdrive


def run_pysmm(year, month, day, out_att_name):
    # Get SEPAL user
    user = getpass.getuser()

    download_to_sepal = os.path.join(os.getcwd(), 'scripts/download_to_sepal.py')

    def export_images(tasks_file_name, out_path):
        
        process = subprocess.Popen(['python3',  download_to_sepal,
                                    tasks_file_name,
                                    out_path
                                ],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, 
                                universal_newlines=True,
                                preexec_fn=os.setpgrp) 
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

    if year != 'False':
            
        year = list_to_int(year)
        month = list_to_int(month)
        day = list_to_int(day)

        if len(year)<2:
            year, month, day = year[0], month[0], day[0]
            single_date = True

        else:
            start_date = datetime.datetime(year[0], month[0], day[0]).date()
            stop_date = datetime.datetime(year[1], month[1], day[1]).date()
    else:
        year, month, day = False, False, False



    # Set the sufix and prefix names
    aoi, field, column  = ast.literal_eval(out_att_name)
    file_sufix = f"{user}_{field}"
    selected_feature = str(int(field))
    aoi_name = aoi.split('/')[-1]


    # Read EE coordinates
    ee.Initialize()
    aoi_ee = ee.FeatureCollection(aoi).filterMetadata(column, 'equals', float(field))\
                .geometry()


    study_area = aoi_ee.bounds().coordinates()

    coords = study_area.get(0).getInfo()
    ll, ur = coords[0], coords[2]
    minlon, minlat, maxlon, maxlat = ll[0], ll[1], ur[0], ur[1]


    # Create a folder to download the pysmm images
    out_path = os.path.join(os.path.expanduser('~'), 'pysmm_downloads',
                            '0_raw', aoi_name, selected_feature)
    if not os.path.exists(out_path):
        os.makedirs(out_path)

    # Download SM maps to GEE


    args=(minlon, minlat, maxlon, maxlat, out_path)
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
        
        kwargs['year']= year
        kwargs['month']=month
        kwargs['day']=day
        tasks = get_map(*args, **kwargs)

    # To get the the series map in row
    else:

        # To get the series map in a specified range
        if start_date:
            kwargs['start_date'] = start_date
            kwargs['stop_date'] = stop_date
            tasks = get_map(*args, **kwargs)

        # To retreive the entire series
        else:
            tasks = get_map(*args, **kwargs)

    if tasks:
        now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        tasks_file_name = os.path.join(out_path, f'task_{now}.txt')

        with open(tasks_file_name, 'w') as tasks_file:
            for item in tasks:
                tasks_file.write(f"{item}")
        tasks_file.close()
        process = export_images(tasks_file_name, out_path)
        print(f'The images are being processed into your GEE account.\n')
        print(f'You can close your SEPAL session and use the SEPAL download tool.\n')

    del tasks



