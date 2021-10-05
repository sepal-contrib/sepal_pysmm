from traitlets import observe, link
from ipywidgets import Output
import ipyvuetify as v

import sepal_ui.sepalwidgets as sw
import sepal_ui.scripts.utils as su
from sepal_ui.aoi import AoiTile

from component.scripts import run_pysmm
from component.message import cm


__all__ = ["ProcessTile"]


class ProcessTile(v.Stepper):
    def __init__(self, model, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.model = model

        titles = [
            [cm.process_tile.landing_tab.title, cm.process_tile.landing_tab.desc],
            ["", ""],
            [cm.process_tile.date_tab.title, cm.process_tile.date_tab.desc],
            [cm.process_tile.start_tab.title, cm.process_tile.start_tab.desc],
        ]

        self.aoi_tile = AoiTile(methods=["-POINTS"])
        self.aoi_tile.view.w_asset.default_asset = (
            "users/dafguerrerom/ReducedAreas_107PHU"
        )

        date_view = DatePickerView(model=model)
        process_view = ProcessView(model=model, aoi_model=self.aoi_tile.view.model)

        content = ['', self.aoi_tile, date_view, process_view]

        stepper_headers = [
            "Introduction",
            "AOI selection",
            "Date selection",
            "Run proces",
        ]
        stepper_header = v.StepperHeader(
            children=[
                v.StepperStep(
                    key=key, complete=False, step=key, editable=True, children=[title]
                )
                for key, title in enumerate(stepper_headers, 1)
            ]
        )

        self.children = [
            stepper_header,
            v.StepperItems(
                children=[
                    StepperContent(key, content[0], content[1])
                    for key, content in enumerate(zip(titles, content), 1)
                ]
            ),
        ]

class ProcessView(v.Card):
    def __init__(self, model, aoi_model, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.model = model
        self.aoi_model = aoi_model

        self.output = Output()
        self.btn = sw.Btn("Start")
        self.alert = sw.Alert()

        self.children = [self.alert, self.btn, self.output]

        self.btn.on_event("click", self.run_process)
    
    @su.loading_button()
    def run_process(self, widget, event, data):

        with self.output:
            self.output.clear_output()
            run_pysmm.run_pysmm(self.aoi_model, self.model, self.alert)


class StepperContent(v.StepperContent):
    def __init__(self, key, title, content, *args, **kwargs):

        self.key = key
        self.step = key
        
        children = [
            v.CardTitle(children=[sw.Markdown(title[0])]),
            v.CardText(children=[sw.Markdown(title[1])]),
        ] + [content] if title[0] else [content]
        
        self.children = [
            v.Card(children=children)
        ]

        super().__init__(*args, **kwargs)

