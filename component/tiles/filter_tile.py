from pathlib import Path

import ipyvuetify as v
import sepal_ui.scripts.utils as su
import sepal_ui.sepalwidgets as sw

import component.parameter as param
import component.scripts.filter_closing_smm as cls_filter
import component.widget as cw
from component.message import cm

__all__ = ["FilterTile"]


class FilterTile(v.Layout, sw.SepalWidget):
    def __init__(self, *args, **kwargs):
        self.class_ = "d-block"
        self._metadata = {"mount_id": "filter"}

        super().__init__(*args, **kwargs)

        self.filter_view = FilterView()

        self.children = [
            v.Card(
                class_="mb-2",
                children=[
                    v.CardTitle(children=[sw.Markdown(cm.filter_tile.title)]),
                    v.CardText(children=[sw.Markdown(cm.filter_tile.desc)]),
                ],
            ),
            self.filter_view,
        ]


class FilterView(v.Card):
    def __init__(self, *args, **kwargs):
        self.counter = 0
        self.min_height = "600px"
        self.class_ = "pa-2"

        super().__init__(*args, **kwargs)

        self.btn = sw.Btn("Apply morphological filter", class_="mb-2")
        self.alert = cw.Alert()

        self.w_selector_view = cw.FolderSelectorView(
            folder=param.RAW_DIR, wildcard="[!.]*.tif"
        )
        self.w_selector = self.w_selector_view.w_selector

        self.children = [
            v.Row(
                children=[
                    v.Col(
                        children=[
                            self.w_selector_view,
                        ]
                    ),
                    v.Col(
                        children=[
                            v.Card(
                                children=[
                                    v.CardTitle(children=["Process"]),
                                    self.btn,
                                    self.alert,
                                ]
                            )
                        ]
                    ),
                ]
            )
        ]

        self.btn.on_event("click", self.on_click)

    @su.loading_button()
    def on_click(self, *args):
        """Run filter script."""
        process_path = self.w_selector.v_model
        recursive = self.w_selector_view.w_recursive.v_model

        # reinitialize the counter
        self.counter = 0

        if not process_path:
            raise Exception("Please select a folder containing .tif images.")

        image_files = [
            str(image)
            for folder in process_path
            for image in (
                list(Path(folder).glob("[!.]*.tif"))
                if not recursive
                else list(Path(folder).rglob("[!.]*.tif"))
            )
        ]

        if not image_files:
            raise Exception(
                "Error: The given folders doesn't have any .tif image to process, "
                "please make sure you have processed and downloaded the images, in the "
                "step 1 and 2. Or try with a different folder."
            )
        else:
            dimension = cls_filter.get_dimension(image_files[0])
            self.alert.add_msg(
                f"There are {len(image_files)} images to process, please wait...",
                type_="info",
            )
            self.alert.append_msg(
                f"The image dimension is {dimension[0]} x {dimension[1]} px"
            )

        for image in image_files:
            cls_filter.raw_to_processed(image, self.alert)
            self.counter += 1
            # self.alert.update_progress(self.counter, total=len(image_files))

        self.alert.append_msg(
            "All the images were correctly processed.", type_="success"
        )