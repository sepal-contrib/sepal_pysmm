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

import logging
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)


def run_pysmm(Aoi, Date, Alert):
    """ Process the input variables to start the "derive_sm" module.

    Args:

        Aoi: 
        Date:    
    """

    # Get SEPAL user
    user = getpass.getuser()

    download_to_sepal = os.path.join(os.getcwd(), 'scripts/download_to_sepal.py')

    def export_images(tasks_file_name, outpath):
        
        process = subprocess.Popen(['python3',  download_to_sepal,
                                    tasks_file_name,
                                    outpath
                                ],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, 
                                universal_newlines=True,
                                preexec_fn=os.setpgrp) 
        return process




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

    single_date = False
    start_date = False

    if Date.date_method == 'Single date':
        
        single_date = True
        year = Date.single_date.year
        month = Date.single_date.month
        day = Date.single_date.day

    elif Date.date_method == 'Range':

        start_date = Date.start_date
        stop_date = Date.end_date

    else:
        # The selected attribute is all time series
        year, month, day = False, False, False


    # Set the sufix and prefix names
    aoi = Aoi.assetId
    field = Aoi.field
    column = Aoi.column

    file_sufix = f"{user}_{field}"
    aoi_name = aoi.split('/')[-1]


    # Read EE coordinates

    selected_feature = Aoi.get_selected_feature()
    minlon, minlat, maxlon, maxlat = Aoi.get_bounds(selected_feature)


    # Create a folder to download the pysmm images
    outpath = os.path.join(os.path.expanduser('~'), 'pysmm_downloads',
                            '0_raw', str(aoi_name), str(field))

    if not os.path.exists(outpath):
        os.makedirs(outpath)

    # Download SM maps to GEE


    args=(minlon, minlat, maxlon, maxlat, outpath, Alert)
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

        #process = export_images(tasks_file_name, outpath) option to export automatically
        Alert.add_msg(f'The images are being processed into your GEE account.\n\
                            You can close your SEPAL session  and use the download tool', type_='success')

    del tasks