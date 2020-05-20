#!/usr/bin/env python3

import argparse
import ast
import ee
import time
import os
import sys
from scripts.utils import gdrive
from tqdm.auto import tqdm

FAILED = 'FAILED'
CANCEL_REQUESTED = 'CANCEL_REQUESTED'
CANCELLED = 'CANCELLED'
COMPLETED = 'COMPLETED'
UNKNOWN = 'UNKNOWN'


def run(task_file, out_path, overwrite=False, rmdrive=False):

    ee.Initialize()

    to_remove_states = {CANCEL_REQUESTED, CANCELLED, FAILED, COMPLETED, UNKNOWN}

    tasks = []
    with open(task_file, "r") as tf:
        for line in tf:
            tasks.append([x.strip() for x in line.split(",")])

    drive_handler = gdrive()

    def remove_from_list(task_to_remove):
        with open(task_file, "r") as f:
            lines = f.readlines()

        # Overwrite the file without the task to remove
        with open(task_file, "w") as f:
            for line in lines:
                if task_to_remove not in line:
                    f.write(line)

    def check_for_not_completed(task):

        state = ee.data.getTaskStatus(task[0])[0]['state']
        file_name = task[1]

        
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
                    remove_from_list(task[0])
                    drive_handler.delete_file(items_to_search, f'{file_name}.tif')
            elif state in [UNKNOWN, FAILED]:
                print(task, state)
            return False
        return True



    def download(tasks):
        while tasks:
            pbar.desc = f'Retrieving tasks status...'
            global items_to_search
            items_to_search = drive_handler.get_items()
            tasks  = list(filter(check_for_not_completed, tasks))
            if tasks:
                pbar.desc = f'Waiting...'
                time.sleep(60)
        


    global pbar
    pbar = tqdm(total = len(tasks), desc="Downloading files...", ncols=700,  bar_format="{l_bar}{bar}{r_bar}")
    download(tasks)
    pbar.desc = 'Done!'
    pbar.close()