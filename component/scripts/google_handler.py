import io
import json
import logging
from pathlib import Path
import time
import os

import ee
import numpy as np
from apiclient import discovery
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaIoBaseDownload

logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)

FAILED = "FAILED"
CANCEL_REQUESTED = "CANCEL_REQUESTED"
CANCELLED = "CANCELLED"
COMPLETED = "COMPLETED"
UNKNOWN = "UNKNOWN"
RUNNING = "RUNNING"

STATES = {FAILED, CANCEL_REQUESTED, CANCELLED, COMPLETED, UNKNOWN, RUNNING}


class ImageDownloader:
    def __init__(
        self,
        task_file,
        overwrite,
        remove_from_drive,
        alert,
        status_span,
        success_span,
        error_span,
        running_span,
    ):
        self.task_file = task_file
        self.overwrite = overwrite
        self.remove_from_drive = remove_from_drive
        self.alert = alert
        self.error_span = error_span
        self.success_span = success_span
        self.running_span = running_span
        self.status_span = status_span

        self.download_counter = 0
        self.failed_counter = 0

        self.drive_handler = GDrive()
        self.out_path = os.path.split(task_file)[0]

        self.stop_event = None

    def download_to_sepal(self, stop_event):
        """
        Download images from Google Drive to SEPAL.

        It will loop over the task file and download the images if they have a status of COMPLETED.

        """
        self.stop_event = stop_event

        tasks = self.read_tasks_from_file()

        if tasks:
            self.download_images(tasks)

            if self.stop_event.is_set():
                return

            type_color = "warning" if self.failed_counter else "success"
            self.alert.append_msg(
                f"Downloaded {self.download_counter} images, {self.failed_counter} tasks failed",
                type_=type_color,
            )
        else:
            self.alert.append_msg(
                "All the images were already downloaded.", type_="warning"
            )

    def read_tasks_from_file(self):
        tasks = []
        with open(self.task_file, "r") as tf:
            for line in tf:
                tasks.append([x.strip() for x in line.split(",")])
        return tasks

    def check_for_not_completed(self, task):
        if self.stop_event.is_set():
            return True

        state = ee.data.getTaskStatus(task[0])[0]["state"]

        file_name = task[1]

        if state in [RUNNING]:
            self.running_span.update()
            return True

        if state in STATES:
            if state == COMPLETED:
                self.download_image(file_name)

            elif state in [UNKNOWN, FAILED]:
                self.failed_counter += 1
                self.error_span.update()

            return False

        return True

    def download_image(self, file_name):
        output_file = os.path.join(self.out_path, f"{file_name}.tif")
        items_to_search = self.drive_handler.get_items()

        if not self.overwrite and os.path.exists(output_file):
            self.status_span.children = [f"Skipping: {file_name}"]
            return

        self.drive_handler.download_file(
            f"{file_name}.tif", output_file, items_to_search
        )

        if self.remove_from_drive:
            self.status_span.children = [f"Removing from drive: {file_name}"]
            self.drive_handler.delete_file(items_to_search, f"{file_name}.tif")

        self.success_span.update()
        self.download_counter += 1

    def download_images(self, tasks):
        self.success_span.reset()
        self.success_span.set_total(len(tasks))
        self.alert.show()

        while tasks and not self.stop_event.is_set():
            self.status_span.children = ["Retrieving tasks status..."]

            self.running_span.reset()

            tasks = list(filter(self.check_for_not_completed, tasks))
            if tasks and not self.stop_event.is_set():
                self.status_span.children = ["Waiting..."]
                time.sleep(5)
            else:
                break


class GDrive:
    def __init__(self):
        self.initialize = ee.Initialize()

        home_path = Path.home()
        credentials_file = (
            ".config/earthengine/credentials"
            if "sepal-user" in home_path.name
            else ".config/earthengine/sepal_credentials"
        )
        credentials_path = home_path / credentials_file

        self.access_token = json.loads((credentials_path).read_text()).get(
            "access_token"
        )
        self.service = discovery.build(
            serviceName="drive",
            version="v3",
            cache_discovery=False,
            credentials=Credentials(self.access_token),
        )

    def print_file_list(self):
        service = self.service

        results = (
            service.files()
            .list(pageSize=30, fields="nextPageToken, files(id, name)")
            .execute()
        )
        items = results.get("files", [])
        if not items:
            print("No files found.")
        else:
            print("Files:")
            for item in items:
                print("{0} ({1})".format(item["name"], item["id"]))

    def get_items(self):
        service = self.service

        # get list of files
        results = (
            service.files()
            .list(
                q="mimeType='image/tiff'",
                pageSize=1000,
                fields="nextPageToken, files(id, name)",
            )
            .execute()
        )
        items = results.get("files", [])

        return items

    def get_id(self, items_to_search, filename):
        items = items_to_search
        # extract list of names and id and find the wanted file
        namelist = np.array([items[i]["name"] for i in range(len(items))])
        idlist = np.array([items[i]["id"] for i in range(len(items))])
        file_pos = np.where(namelist == filename)

        if len(file_pos[0]) == 0:
            return (0, filename + " not found")
        else:
            return (1, idlist[file_pos])

    def download_file(self, filename, localpath, items_to_search):
        service = self.service

        # get file id
        success, fId = self.get_id(items_to_search, filename)
        if success == 0:
            print(filename + " not found")
            return

        request = service.files().get_media(fileId=fId[0])
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            # print('Download %d%%.' % int(status.progress() * 100))

        fo = open(localpath, "wb")
        fo.write(fh.getvalue())
        fo.close()

    def delete_file(self, items_to_search, filename):
        service = self.service

        # get file id
        success, fId = self.get_id(items_to_search, filename)

        if success == 0:
            print(filename + " not found")

        service.files().delete(fileId=fId[0]).execute()
