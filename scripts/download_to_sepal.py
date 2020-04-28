#!/usr/bin/env python3

import argparse
import ast
import ee
import time
import os
import sys
from utils import gdrive
from tqdm import tqdm


# Create parser arguments


parser = argparse.ArgumentParser()
parser.add_argument('tasks_file', 
                    help ="File with the format TASK_ID, NAME for each line")
parser.add_argument('out_path', 
                    help ="Path in SEPAL to download the processed images")
parser.add_argument('-o', action='store_true',
                    help ="Overwrite existing images",)
parser.add_argument('-rm', action='store_true', 
                    help ="Remove images from Google Drive account",)
args = parser.parse_args()



ee.Initialize()


FAILED = 'FAILED'
CANCEL_REQUESTED = 'CANCEL_REQUESTED'
CANCELLED = 'CANCELLED'
COMPLETED = 'COMPLETED'

to_remove_states = {CANCEL_REQUESTED, CANCELLED, FAILED, COMPLETED}

out_path = args.out_path
overwrite = args.o
rmdrive = args.rm

tasks = []
with open(args.tasks_file, "r") as tasks_file:
    for line in tasks_file:
        tasks.append([x.strip() for x in line.split(",")])

drive_handler = gdrive()


def check_for_not_completed(task):

    state = ee.data.getTaskStatus(task[0])[0]['state']
    file_name = task[1]
    #print(task, state)
    
    if state in to_remove_states:
        if state == COMPLETED:
            output_file = os.path.join(out_path, f'{file_name}.tif')
            pbar.update(1)

            if not overwrite:
                if not os.path.exists(output_file):
                    pbar.desc = f'Downloading: {file_name}'
                    drive_handler.download_file(f'{file_name}.tif',
                                                output_file,
                                                items_to_search)
                else:
                    pbar.desc = f'Skipping: {file_name}'
            else:
                pbar.desc = f'Overwriting: {file_name}'
                drive_handler.download_file(f'{file_name}.tif',
                                            output_file,
                                            items_to_search)
            if rmdrive:
                pbar.desc = f'Removing from drive: {file_name}'
                drive_handler.delete_file(items_to_search, f'{file_name}.tif')

        return False
    return True



def download(tasks):
    while tasks:
        pbar.desc = f'Retrieving images...'
        global items_to_search
        items_to_search = drive_handler.get_items()
        tasks  = list(filter(check_for_not_completed, tasks))
        if tasks:
            pbar.desc = f'Waiting...'
            time.sleep(60)
    


global pbar
pbar = tqdm(total = len(tasks), desc="Downloading files...", bar_format="{l_bar}{bar:30}{r_bar}{bar:-60b}")
download(tasks)
pbar.desc = 'Done!'
pbar.close()