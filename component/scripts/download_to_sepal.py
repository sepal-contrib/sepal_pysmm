#!/usr/bin/env python3

import argparse
import ast
import ee
import time
import os
import sys
from component.scripts.utils import gdrive
from tqdm.auto import tqdm

FAILED = 'FAILED'
CANCEL_REQUESTED = 'CANCEL_REQUESTED'
CANCELLED = 'CANCELLED'
COMPLETED = 'COMPLETED'
UNKNOWN = 'UNKNOWN'

import logging
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)


def run(task_file, alert, output, overwrite=False, rmdrive=False, ):

    out_path = os.path.split(task_file)[0]

    ee.Initialize()

    to_remove_states = {CANCEL_REQUESTED, CANCELLED, FAILED, COMPLETED, UNKNOWN}

    tasks = []
    try:
        with open(task_file, "r") as tf:
            for line in tf:
                tasks.append([x.strip() for x in line.split(",")])
    
    except Exception as e:
        raise Exception(e)

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
                alert.add_msg(f'There was an error task, state', type_='error')
            return False
        return True



    def download(tasks):
        while tasks:
            alert.add_msg('Retrieving tasks status...', type_='info')
            global items_to_search
            items_to_search = drive_handler.get_items()
            tasks  = list(filter(check_for_not_completed, tasks))
            if tasks:
                alert.add_msg('Waiting...', type_='info')
                pbar.set_description('Waiting...')
                time.sleep(45)

    if tasks:
        global pbar
        with output:
            pbar = tqdm(total = len(tasks), desc="Starting...", ncols=700,  bar_format="{l_bar}{bar}{r_bar}")
        download(tasks)
        pbar.set_description('Done!')
        pbar.close()
        alert.add_msg(f'All the images were downloaded succesfully', type_='success')
    else:
        alert.add_msg(f'All the images were already downloaded.', type_='warning')