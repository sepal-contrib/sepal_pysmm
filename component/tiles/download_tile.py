from ipywidgets import Output

import ipyvuetify as v

import sepal_ui.sepalwidgets as sw
import sepal_ui.scripts.utils as su

from component.scripts import download_to_sepal
import component.widget as cw
import component.parameter as param
from component.message import cm

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
    def __init__(self, *args, **kwargs):

        self.class_ = "pa-2"

        super().__init__(*args, **kwargs)

        self.alert = sw.Alert()

        self.w_overwrite = v.Switch(
            v_model=True, inset=True, label="Overwrite SEPAL images"
        )

        self.w_remove = v.Switch(
            v_model=False, inset=True, label="Remove Google Drive Images"
        )

        self.w_selection = sw.FileInput(folder=str(param.RAW_DIR), extentions=[".txt"])

        self.output = Output()
        self.btn = sw.Btn(text="Download", icon="mdi-download")

        self.children = [
            self.w_selection,
            self.w_overwrite,
            self.w_remove,
            self.btn,
            self.alert,
            self.output,
        ]

        self.btn.on_event("click", self.on_download)

    @su.loading_button(debug=True)
    def on_download(self, widget, event, data):

        download_to_sepal.run(
            task_file=self.w_selection.v_model,
            alert=self.alert,
            overwrite=self.w_overwrite.v_model,
            rmdrive=self.w_remove.v_model,
            output=self.output,
        )
