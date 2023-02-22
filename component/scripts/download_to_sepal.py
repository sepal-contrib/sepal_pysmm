import os
import time

import ee

from component.scripts.utils import GDrive

FAILED = "FAILED"
CANCEL_REQUESTED = "CANCEL_REQUESTED"
CANCELLED = "CANCELLED"
COMPLETED = "COMPLETED"
UNKNOWN = "UNKNOWN"

import logging

logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)


def run(task_file, alerts, overwrite=False, rmdrive=False, counter=0):
    counter = counter
    state_alert = alerts[0]
    result_alert = alerts[1]

    out_path = os.path.split(task_file)[0]

    ee.Initialize()

    to_remove_states = {CANCEL_REQUESTED, CANCELLED, FAILED, COMPLETED, UNKNOWN}

    tasks = []
    with open(task_file, "r") as tf:
        for line in tf:
            tasks.append([x.strip() for x in line.split(",")])

    drive_handler = GDrive()

    def remove_from_list(task_to_remove):
        with open(task_file, "r") as f:
            lines = f.readlines()

        # Overwrite the file without the task to remove
        with open(task_file, "w") as f:
            for line in lines:
                if task_to_remove not in line:
                    f.write(line)

    def check_for_not_completed(task):
        state = ee.data.getTaskStatus(task[0])[0]["state"]
        file_name = task[1]

        if state in to_remove_states:
            if state == COMPLETED:
                output_file = os.path.join(out_path, f"{file_name}.tif")

                counter += 1
                result_alert.update_progress(counter, total=len(tasks))

                if not overwrite:
                    if not os.path.exists(output_file):
                        result_alert.append_msg(f"Downloading: {file_name}")
                        drive_handler.download_file(
                            f"{file_name}.tif", output_file, items_to_search
                        )
                    else:
                        result_alert.append_msg(f"Skipping: {file_name}")
                else:
                    result_alert.append_msg(f"Overwriting: {file_name}")
                    drive_handler.download_file(
                        f"{file_name}.tif", output_file, items_to_search
                    )
                if rmdrive:
                    result_alert.append_msg(f"Removing from drive: {file_name}")
                    remove_from_list(task[0])
                    drive_handler.delete_file(items_to_search, f"{file_name}.tif")
            elif state in [UNKNOWN, FAILED]:
                result_alert.add_msg("There was an error task, state", type_="error")
            return False

        return True

    def download(tasks):
        while tasks:
            state_alert.add_msg("Retrieving tasks status...", type_="info")
            global items_to_search
            items_to_search = drive_handler.get_items()
            tasks = list(filter(check_for_not_completed, tasks))
            if tasks:
                state_alert.add_msg("Waiting...", type_="info")
                time.sleep(45)

    if tasks:
        download(tasks)
        result_alert.append_msg(
            "All the images were downloaded succesfully", type_="success"
        )

    else:
        result_alert.append_msg(
            "All the images were already downloaded.", type_="warning"
        )
