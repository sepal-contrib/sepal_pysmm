import ipyvuetify as v
import sepal_ui.scripts.utils as su
import sepal_ui.sepalwidgets as sw
from sepal_ui.aoi import AoiTile
from traitlets import Int

import component.widget as cw
from component.message import cm
from component.scripts import run_pysmm
from component.scripts.resize import rt
from component.widget.count_span import CountSpan

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
            label="Grid size (deg)",
            v_model=2,
            min=0.1,
            max=5,
            step=0.1,
            class_="mb-2",
            thumb_label="always",
            disabled=True,
        )

        self.w_grid = v.Switch(
            label="Create chips",
            v_model=False,
            class_="mb-2 mt-0 mr-2",
        )

        self.w_grid.observe(
            lambda chg: setattr(self.w_grid_size, "disabled", not chg["new"]), "v_model"
        )

        w_grid = v.Flex(
            class_="d-flex",
            children=[self.w_grid, self.w_grid_size],
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
                                        w_grid,
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

    @su.loading_button()
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
            chip_process=self.w_grid.v_model,
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
