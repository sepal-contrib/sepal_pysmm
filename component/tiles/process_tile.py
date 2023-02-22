import ipyvuetify as v

import sepal_ui.sepalwidgets as sw
import sepal_ui.scripts.utils as su
from sepal_ui.aoi import AoiTile

import component.widget as cw
from component.scripts import run_pysmm
from component.message import cm
from component.scripts.resize import rt

__all__ = ["ProcessTile"]


class ProcessTile(sw.Stepper):
    def __init__(self, model, *args, **kwargs):

        self._metadata = {"mount_id": "process"}

        super().__init__(*args, **kwargs)
        
        self.model = model

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
            self.model,
            self.aoi_tile.view.model, 
            self.date_view,
            attributes = {"id": "process_view"},
        )

        content = ["", self.aoi_tile, self.date_view, process_view]

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
                style_="background:#1e1e1e;",
                children=[
                    StepperContent(key, content[0], content[1])
                    for key, content in enumerate(zip(titles, content), 1)
                ]
            ),
        ]
        display(rt)
        # Trigger resize event when AOI selection header button is clicked
        stepper_header.children[1].on_event("click", lambda *args: rt.resize())


class ProcessView(v.Layout):

    counter = 0
    "int: counter to keep track of the number of images already processed by run_pysmm function."

    def __init__(self, model, aoi_model, date_model, *args, **kwargs):
        self.class_ = "pa-2 d-block"

        super().__init__(*args, **kwargs)
        
        self.model = model
        self.aoi_model = aoi_model
        self.date_model = date_model
        self.counter = 0
        self.w_ascending = v.RadioGroup(
            label='Select an orbit:',
            row=True,
            v_model=False,
            children=[
                v.Radio(label="Ascending", value=True),
                v.Radio(label="Descending", value=False),
            ],
        )
        
        self.btn = sw.Btn("Start process", class_="mb-2")
        self.alert = cw.Alert()
        
        self.model.bind(self.w_ascending, "ascending")

        self.children = [self.w_ascending, self.btn, self.alert]

        self.btn.on_event("click", self.run_process)

    @su.loading_button(debug=True)
    def run_process(self, widget, event, data):
        
        # Restart counter everytime the process is run
        self.counter = 0
        run_pysmm.run_pysmm(
            self.aoi_model, self.date_model, self.model, self.alert, self.counter
        )


class StepperContent(v.StepperContent):
    def __init__(self, key, title, content, *args, **kwargs):

        self.key = key
        self.step = key

        children = (
            [
                v.CardTitle(children=[sw.Markdown(title[0])]),
                v.CardText(children=[sw.Markdown(title[1])]),
            ]
            + [content]
            if title[0]
            else [content]
        )

        self.children = [v.Card(children=children)]

        super().__init__(*args, **kwargs)
