#!/usr/bin/env python3

import argparse
import subprocess
import os
import sys
import ntpath
import re

from time import sleep
from datetime import datetime
from osgeo import gdal
from tqdm.auto import trange, tqdm


def filter_closing(image, tmp_path):

    tmp_image = os.path.join(tmp_path,'tmp_closing.tif')
    process = subprocess.run(['/usr/local/lib/orfeo/bin/otbcli_GrayScaleMorphologicalOperation', 
                                '-in', image,
                                '-out', tmp_image,
                                '-structype', 'ball',
                                '-structype.ball.xradius', '1',
                                '-structype.ball.yradius', '1',
                                '-filter', 'closing'
                            ],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, 
                            universal_newlines=True)
    return process, tmp_image

def gdal_calculation(image, tmp_image, out_path):

    image_name = ntpath.basename(image)
    closed_image = os.path.join(out_path, 'close_'+image_name)

    process = subprocess.run(['gdal_calc.py',
                                '-A', image,
                                '-B', tmp_image,
                                '--NoDataValue=0',
                                '--co=COMPRESS=LZW',
                                '--type=UInt16',
                                '--overwrite',
                                '--outfile='+closed_image,
                                '--calc=B*(A==0)+A'
                            ],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, 
                            universal_newlines=True)
    return process

def remove_tmp_image(tmp_image):
    os.remove(tmp_image)
    return

def get_dimension(image):
    raster = gdal.Open(image)
    return [raster.RasterXSize, raster.RasterYSize]

def raw_to_processed(image):

    image_name = ntpath.basename(image)
    out_close_path = os.path.dirname(os.path.abspath(image)) \
                    .replace('0_raw', '1_processed')

    if not os.path.exists(out_close_path):
        os.makedirs(out_close_path)

    if not os.path.exists(os.path.join(out_close_path, 'close_'+image_name)):
        message = f'\b\rProcessing: {image_name}...'
        sys.stdout.write(message)
        filter_process, tmp_image = filter_closing(image, out_close_path)
        if filter_process.returncode == 0:
            gdal_process = gdal_calculation(image, tmp_image, out_close_path)
            if gdal_process.returncode == 0:
                remove_tmp_image(tmp_image)
            else:    
                print(gdal_process.stderr)
        else:
            message = "\b\rThe process couldn't be completed"
            sys.stdout.write(message)
            print(filter_process.stderr)
    else:
        message = f'\b\rSkipping: Image "{image_name}" already exists'
        sys.stdout.write(message)

    
    sleep(0.01)
    sys.stdout.write("\b\r"+" "*(len(message)))
    sys.stdout.flush()
    return 

def run_filter(process_path, alert):

    IMAGES_TYPES = ('.tif')
    folder = process_path
    image_files = []
    if os.path.isdir(folder):
        for root, dirs, files in os.walk(folder):
            if len(files) != 0:
                files = [os.path.join(root, x) for x in files if x.endswith(IMAGES_TYPES)]
                [image_files.append(os.path.abspath(file)) for file in files]
        image_files.sort()
    
    else:
        alert.add_msg(f'ERROR: The {folder} is not a directory path.', type_='error')
    
    if len(image_files) > 0:
        dimension = get_dimension(image_files[0])
        alert.add_msg(f'There are {len(image_files)} images to process, please wait...', type_='info')
        print(f'The image dimension is {dimension[0]} x {dimension[1]} px')

    else:
        alert.add_msg(f'Error: The folder: "{folder}" is empty, please \
         make sure you have processed and downloaded the images.', type_='error')
        return

    try:
        for i in trange(len(image_files)):
            raw_to_processed(image_files[i])

        alert.add_msg(f'All the images were correctly processed.', type_='success')

    except Exception as e:
        alert.add_msg(f'{e}', type_='error')
        return

    return 0