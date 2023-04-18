import ipyvuetify as v
import sepal_ui.scripts.utils as su
import sepal_ui.sepalwidgets as sw
from sepal_ui.aoi import AoiTile
from traitlets import Int

import component.widget as cw
from component.message import cm
from component.scripts import run_pysmm
from component.scripts.resize import rt

__all__ = ["ProcessTile"]


class ProcessTile(sw.Stepper):
    def __init__(self, model, *args, **kwargs):
        self._metadata = {"mount_id": "process"}
        self.attributes = {"id": "process_tile"}

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
            attributes={"id": "process_view"},
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
                ],
            ),
        ]
        display(rt)
        # Trigger resize event when AOI selection header button is clicked
        stepper_header.children[1].on_event("click", lambda *args: rt.resize())


class ProcessView(v.Layout):
    def __init__(self, model, aoi_model, date_model, *args, **kwargs):
        self.class_ = "pa-2 d-block"

        super().__init__(*args, **kwargs)

        self.model = model
        self.aoi_model = aoi_model
        self.date_model = date_model
        self.counter = 0
        self.w_ascending = v.RadioGroup(
            label="Select an orbit:",
            row=True,
            v_model=False,
            children=[
                v.Radio(label="Ascending", value=True),
                v.Radio(label="Descending", value=False),
            ],
        )

        # Define HTML spans. These will be added to the alert view after
        # some initial messages are displayed
        self.images_span = CountSpan("Images")
        self.chips_span = CountSpan("chips")

        question_icon = v.Icon(children=["mdi-help-circle"], small=True)

        self.btn = sw.Btn("Start process", class_="my-2")
        self.alert = cw.Alert()

        self.model.bind(self.w_ascending, "ascending")

        # Define a sw.Slider to control the grid size
        self.w_grid_size = sw.Slider(
            label="Grid size",
            v_model=0.5,
            min=0.1,
            max=2,
            step=0.1,
            class_="mb-2",
            thumb_label="always",
        )

        # Add grid_size and w_ascending to an expansion panel as advanced options
        advanced_options = v.ExpansionPanels(
            class_="mb-2",
            v_model=False,
            children=[
                v.ExpansionPanel(
                    children=[
                        v.ExpansionPanelHeader(children=["Advanced options"]),
                        v.ExpansionPanelContent(
                            children=[
                                v.Flex(
                                    class_="d-flex align-center",
                                    children=[
                                        self.w_grid_size,
                                        sw.Tooltip(
                                            question_icon,
                                            cm.help.grid_size,
                                            left=True,
                                            max_width=300,
                                        ),
                                    ],
                                ),
                                v.Flex(
                                    class_="d-flex",
                                    children=[
                                        self.w_ascending,
                                        sw.Tooltip(
                                            question_icon,
                                            cm.help.orbit,
                                            right=True,
                                            max_width=300,
                                        ),
                                    ],
                                ),
                            ]
                        ),
                    ]
                )
            ],
        )

        self.children = [
            advanced_options,
            self.btn,
            self.alert,
        ]

        self.btn.on_event("click", self.run_process)

    @su.loading_button(debug=True)
    def run_process(self, widget, event, data):
        # Restart counter everytime the process is run

        self.images_span.reset()
        self.chips_span.reset()

        run_pysmm.run_pysmm(
            self.aoi_model,
            self.date_model,
            self.model,
            self.alert,
            self.images_span,
            self.chips_span,
            self.w_grid_size.v_model,
        )


class CountSpan(sw.Html):
    """HTML span component to control the number of images or chips that have been processed"""

    value = Int(0).tag(sync=True)
    total = Int(0).tag(sync=True)

    def __init__(self, name, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.tag = "span"
        self.name = name + ": "
        self.children = self.get_value()

    def get_value(self):
        """Get the value of the span"""
        return [self.name, f"{self.value}/{self.total}"]

    def update(self):
        """Update the value of the span"""
        self.value += 1
        self.children = self.get_value()

    def set_total(self, total):
        """Set the total value of the span"""
        self.total = total
        self.children = self.get_value()

    def reset(self):
        """Reset the value of the span"""
        self.value = -1
        self.total = 0
        self.update()


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
