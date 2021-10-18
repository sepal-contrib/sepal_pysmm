from pathlib import Path
from ipywidgets import Output, Layout
import ipyvuetify as v

import sepal_ui.sepalwidgets as sw
import sepal_ui.scripts.utils as su

import component.widget as cw
from component.message import cm
import component.parameter as param

from component.scripts.filter_closing_smm import run_filter

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

        self.min_height = "600px"
        self.class_ = "pa-2"

        super().__init__(*args, **kwargs)

        self.output = Output()
        self.btn = sw.Btn("Apply morphological filter", class_="mb-2")
        self.alert = sw.Alert()

        w_selector_view = cw.FolderSelectorView(
            folder=param.RAW_DIR, max_depth=0, wildcard="[!.]*.tif"
        )
        self.w_selector = w_selector_view.w_selector

        self.children = [
            v.Row(
                children=[
                    v.Col(
                        children=[
                            w_selector_view,
                        ]
                    ),
                    v.Col(
                        children=[
                            v.Card(
                                children=[
                                    v.CardTitle(children=["Process"]),
                                    self.btn,
                                    self.output,
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
    def on_click(self, widget, event, data):

        run_filter(self.w_selector.v_model, self.alert, self.output)

        self.alert.add_msg(f"All the images were correctly processed.", type_="success")
