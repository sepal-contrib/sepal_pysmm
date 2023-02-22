from ipywidgets import Output

import ipyvuetify as v

import sepal_ui.sepalwidgets as sw
import sepal_ui.scripts.utils as su

import component.parameter as param
from component.message import cm
import component.widget as cw

import ee
import time
import os
from component.scripts.utils import GDrive

FAILED = "FAILED"
CANCEL_REQUESTED = "CANCEL_REQUESTED"
CANCELLED = "CANCELLED"
COMPLETED = "COMPLETED"
UNKNOWN = "UNKNOWN"

import logging

logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)

__all__ = ["DownloadTile"]


class DownloadTile(v.Layout, sw.SepalWidget):
    def __init__(self, *args, **kwargs):

        self.class_ = "d-block"
        self._metadata = {"mount_id": "download"}

        super().__init__(*args, **kwargs)

        self.download_view = DownloadView()

        self.children = [
            v.Card(
                class_="mb-2",
                children=[
                    v.CardTitle(children=[cm.download_tile.title]),
                    v.CardText(children=[sw.Markdown(cm.download_tile.description)]),
                ],
            ),
            self.download_view,
        ]


class DownloadView(v.Card):


    counter = 0
    "int: counter to keep track of the number of images downloaded"

    def __init__(self, *args, **kwargs):

        self.class_ = "pa-2"

        super().__init__(*args, **kwargs)

        self.alert = cw.Alert()
        self.result_alert = cw.Alert()

        self.w_overwrite = v.Switch(
            v_model=True, label="Overwrite SEPAL images", small=True,
            class_="mr-4"
        )

        self.w_remove = v.Switch(
            v_model=False, label="Remove images from Google Drive", small=True
        )

        self.w_selection = sw.FileInput(folder=str(param.RAW_DIR), extentions=[".txt"])

        self.btn = sw.Btn(text="Download", icon="mdi-download")

        self.children = [
            self.w_selection,
            sw.Flex(
                class_="d-flex",
                children=[
                    self.w_overwrite,
                    self.w_remove,
                ]
            ),
            self.btn,
            self.alert,
            self.result_alert
        ]

        self.btn.on_event("click", self.download_to_sepal)

    @su.loading_button(debug=True)
    def download_to_sepal(self, *args): 
        """Download images from Google Drive to SEPAL. It will loop over the task file 
        and download the images if they have a status of COMPLETED.
        """

        task_file=self.w_selection.v_model
        alerts=[self.alert, self.result_alert]
        overwrite=self.w_overwrite.v_model
        rmdrive=self.w_remove.v_model

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

                    self.counter += 1
                    result_alert.update_progress(self.counter, total=len(tasks))

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
                    result_alert.add_msg(f"There was an error task, state", type_="error")
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
            state_alert.reset()
            result_alert.append_msg(f"All the images were downloaded succesfully", type_="success")
        else:
            state_alert.reset()
            result_alert.append_msg(f"All the images were already downloaded.", type_="warning")

