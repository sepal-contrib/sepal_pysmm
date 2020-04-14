#!/usr/bin/env python3

import argparse
import subprocess
import os
import ntpath
import re
from datetime import datetime

def run(folder):

    IMAGES_TYPES = ('.tif')

    #parser = argparse.ArgumentParser()
    #parser.add_argument('folder', type=str, 
    #                    help='directories or images files to process')
    #args = parser.parse_args()

    #folder = args.folder

    def extract_image_info(image):

        image_name = ntpath.basename(image)
        match = re.search(r'\d{4}_\d{2}_\d{2}', image_name) 
        image_date = datetime.strptime(match.group(), '%Y_%m_%d').date()

        return image_name, image_date

    def filter_closing(image, tmp_path):

        tmp_image = os.path.join(tmp_path,'tmp_closing.tif')
        process = subprocess.run(['/usr/local/lib/orfeo/bin/otbcli_GrayScaleMorphologicalOperation', 
                                    '-in', image,
                                    '-out', tmp_image,
                                    '-structype', 'ball',
                                    '-xradius', '1',
                                    '-yradius', '1',
                                    '-filter', 'closing'
                                ],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, 
                                universal_newlines=True)
        return process, tmp_image

    def gdal_calculation(image, tmp_image, out_path):

        image_name = extract_image_info(image)[0]
        closed_image = os.path.join(out_path, 'close_'+image_name)

        process = subprocess.run(['gdal_calc.py',
                                    '-A', image,
                                    '-B', tmp_image,
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

    def raw_to_processed(image):

        image_name = extract_image_info(image)[0]
        out_close_path = os.path.dirname(os.path.abspath(image)) \
                        .replace('raw', '1_processed')

        if not os.path.exists(out_close_path):
            os.makedirs(out_close_path)

        if not os.path.exists(os.path.join(out_close_path, 'close_'+image_name)):
            filter_process, tmp_image = filter_closing(image, out_close_path)

            if filter_process.returncode == 0:
                gdal_process = gdal_calculation(image, tmp_image, out_close_path)

                if gdal_process.returncode == 0:
                    print(f'Image: {image_name} processed.')
                    remove_tmp_image(tmp_image)
                else:    
                    print(gdal_process.stderr)
            else:
                print("The process couldn't be completed")
                print(filter_process.stderr)
        else:
            print(f'Skipping: Image "{image_name}" already exists')
        return 


    # Search all Image files in inputs recursively if the files are in directories

    image_files = []    

    if os.path.isdir(folder):
        for root, dirs, files in os.walk(folder):
            if len(files) != 0:
                files = [os.path.join(root, x) for x in files if x.endswith(IMAGES_TYPES)]
                [image_files.append(os.path.abspath(file)) for file in files]
    else:
        print(f'ERROR: The {folder} joined is not a directory path.')
    print(f'There are {len(image_files)} images to process, please wait...')

    dates = []
    for image in image_files:
        dates.append(extract_image_info(image))
        raw_to_processed(image)

    print('Done!')