import os
from pathlib import Path

import ipyvuetify as v
import sepal_ui.mapping as sm
import sepal_ui.scripts.utils as su
import sepal_ui.sepalwidgets as sw

from component.message import cm
from component.parameter.directory import BASE_DIR


class MapTile(sw.Card):
    def __init__(self, *args, **kwargs):
        self._metadata = {"mount_id": "map"}
        self.attributes = {"id": "map_tile"}

        super().__init__(*args, **kwargs)

        self.file_chooser = sw.FileInput(extentions=[".tif"], folder=Path(BASE_DIR))

        self.map_ = sm.SepalMap(basemaps=["SATELLITE"], vinspector=True)

        self.btn = sw.Btn(text="Display image", class_="block")
        self.alert = sw.Alert()
        self.btn.on_event("click", self.display_image)

        self.children = [
            v.CardTitle(children=[sw.Markdown(cm.map_tile.title)]),
            v.CardText(children=[sw.Markdown(cm.map_tile.desc)]),
            self.file_chooser,
            self.btn,
            self.alert,
            v.Divider(class_="mt-5"),
            self.map_,
        ]

    @su.loading_button()
    def display_image(self, widget, event, data):
        image = self.file_chooser.file
        image_path = Path(image)
        layer_name = image_path.stem

        if os.path.exists(image):
            self.map_.remove_last_layer(local=True)
            self.map_.add_raster(image, layer_name=layer_name)
        else:
            self.alert.add_msg("Please select a valid image", type_="error")
