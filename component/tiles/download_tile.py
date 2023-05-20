import logging
import ipyvuetify as v
import sepal_ui.scripts.utils as su
import sepal_ui.sepalwidgets as sw

import component.parameter as param
import component.widget as cw
from component.message import cm
import component.scripts.google_handler as goog
from component.scripts.taks_controller import TaskController
from component.widget.count_span import CountSpan
from component.widget.count_span import DownloadAlert


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

        # Define HTML spans. These will be added to the alert view after
        # some initial messages are displayed
        self.status_span = sw.Html(tag="span", children=[])
        self.success_span = CountSpan("downloaded", with_total=True)
        self.error_span = CountSpan("error", color="error", with_total=False)
        self.running_span = CountSpan("running", with_total=False)

        self.alert = DownloadAlert(
            self.status_span,
            self.success_span,
            self.error_span,
            self.running_span,
        ).hide()

        self.w_overwrite = v.Switch(
            v_model=True, label="Overwrite SEPAL images", small=True, class_="mr-4"
        )

        self.w_remove = v.Switch(
            v_model=False, label="Remove images from Google Drive", small=True
        )

        self.w_selection = sw.FileInput(folder=str(param.RAW_DIR), extentions=[".txt"])

        self.btn = sw.Btn(text="Download", icon="mdi-download", small=True)
        self.stop_btn = sw.Btn(
            text="Stop", small=True, class_="ml-2", color="secondary    "
        )

        self.children = [
            self.w_selection,
            sw.Flex(
                class_="d-flex",
                children=[
                    self.w_overwrite,
                    self.w_remove,
                ],
            ),
            sw.Flex(
                class_="d-flex",
                children=[
                    self.btn,
                    self.stop_btn,
                ],
            ),
            self.alert,
        ]

        self.btn.on_event("click", self.download_to_sepal)

    def download_to_sepal(self, *args):
        """
        Download images from Google Drive to SEPAL.

        It will loop over the task file and download the images
        if they have a status of COMPLETED.

        """
        task_file = self.w_selection.v_model
        overwrite = self.w_overwrite.v_model
        remove_from_drive = self.w_remove.v_model

        # reset alert
        self.alert.reset()

        if not task_file:
            raise ValueError("Please select a task file")

        downloader = goog.ImageDownloader(
            task_file,
            overwrite,
            remove_from_drive,
            self.alert,
            self.status_span,
            self.success_span,
            self.error_span,
            self.running_span,
        )

        task_controller = TaskController(
            self.btn, self.stop_btn, downloader.download_to_sepal
        )

        task_controller.start_task()
