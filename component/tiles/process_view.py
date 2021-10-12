from traitlets import observe, link
from ipywidgets import Output
import ipyvuetify as v

import sepal_ui.sepalwidgets as sw
import sepal_ui.scripts.utils as su
from sepal_ui.aoi import AoiTile

import component.widget as cw
from component.scripts import run_pysmm
from component.message import cm



__all__ = ["ProcessTile"]


class ProcessTile(v.Stepper):
    def __init__(self, model, *args, **kwargs):

        super().__init__(*args, **kwargs)

        titles = [
            [cm.process_tile.landing_tab.title, cm.process_tile.landing_tab.desc],
            ["", ""],
            [cm.process_tile.date_tab.title, cm.process_tile.date_tab.desc],
            [cm.process_tile.start_tab.title, cm.process_tile.start_tab.desc],
        ]

        self.aoi_tile = AoiTile(methods=["-POINTS"])
        self.aoi_tile.view.w_asset.w_file.default_asset = (
            "users/dafguerrerom/ReducedAreas_107PHU"
        )

        self.date_view = cw.DateSelector()
        process_view = ProcessView(
            self.aoi_tile.view.model,
            self.date_view
        )

        content = ['', self.aoi_tile, self.date_view, process_view]

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
    def __init__(self, aoi_model, date_model, *args, **kwargs):
        self.class_ = 'pa-2'
        
        super().__init__(*args, **kwargs)

        self.aoi_model = aoi_model
        self.date_model = date_model

        self.output = Output()
        self.btn = sw.Btn("Start process", class_='mb-2')
        self.alert = sw.Alert()

        self.children = [self.btn, self.alert, self.output]

        self.btn.on_event("click", self.run_process)
    
    @su.loading_button(debug=True)
    def run_process(self, widget, event, data):
        run_pysmm.run_pysmm(self.aoi_model, self.date_model, self.alert, self.output)


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

