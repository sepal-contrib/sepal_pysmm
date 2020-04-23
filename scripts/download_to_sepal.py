#!/usr/bin/env python3

import argparse
import ast
import ee
import time
import os
from utils import gdrive

# Create parser arguments


parser = argparse.ArgumentParser()
parser.add_argument('tasks_file', 
                    help ="File with the format TASK_ID, NAME for each line")
parser.add_argument('out_path', 
                    help ="Path in SEPAL to download the processed images")
args = parser.parse_args()

ee.Initialize()

FAILED = 'FAILED'
CANCEL_REQUESTED = 'CANCEL_REQUESTED'
CANCELLED = 'CANCELLED'
COMPLETED = 'COMPLETED'

to_remove_states = {CANCEL_REQUESTED, CANCELLED, FAILED, COMPLETED}

out_path = args.out_path

tasks = []
with open(args.tasks_file, "r") as tasks_file:
    for line in tasks_file:
        tasks.append([x.strip() for x in line.split(",")])

print(tasks)

drive_handler = gdrive()

def check_for_not_completed(task):

    state = ee.data.getTaskStatus(task[0])[0]['state']
    file_name = task[1]
    print(task, state)
    
    if state in to_remove_states:
        if state == COMPLETED:
            output_file = os.path.join(out_path, f'{file_name}.tif')
            if not os.path.exists(output_file):
                print('Downloading files ...')
                drive_handler.download_file(file_name + '.tif',
                                            output_file,
                                            items_to_search)
            else:
                print(f'Skipping: File {file_name} already exists.')
        return False
    return True

def download(tasks):
    while tasks:
        global items_to_search
        items_to_search = drive_handler.get_items()
        tasks  = list(filter(check_for_not_completed, tasks))
        time.sleep(180)
    print('Done!')

download(tasks)