from os import cpu_count
from pathlib import Path

from traitlets import link
from ipywidgets import Output
import ipyvuetify as v
import sepal_ui.sepalwidgets as sw
import sepal_ui.scripts.utils as su

import component.parameter as param
import component.widget as cw

from component.scripts import stackstat
from component.message import cm

import modules.stackcomposed.stack_composed.parse as ps


class StatisticsTile(v.Card):
    def __init__(self, model, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.model = model

        self.statistics_view = StatisticsView(model=model)

        self.children = [
            v.CardTitle(children=[sw.Markdown(cm.statistics_tile.title)]),
            v.CardText(children=[sw.Markdown(cm.statistics_tile.desc)]),
            self.statistics_view,
        ]


class StatisticsView(v.Layout):

    STATS_DICT = {
        "Median": "median",
        "Mean": "mean",
        "Geometric mean": "Gmean",
        "Maximum": "max",
        "Minimum": "min",
        "Standard deviation": "std",
        "Valid pixels": "valid_pixels",
        "Linear trend": "linear_trend",
    }

    def __init__(self, model, *args, **kwargs):

        self.class_ = "d-block"
        self._metadata = {"mount-id": "data-input"}

        super().__init__(*args, **kwargs)
        
        self.model = model

        self.alert = sw.Alert()
        self.btn = sw.Btn("Calculate statistics")
        self.output = Output()
        self.date_selector = cw.DateSelector(season=True, remove_method=["single"])

        self.w_selector = cw.PathSelector(param.PROCESSED_DIR)

        self.w_stats = v.Select(
            label="Statistic",
            items=[{"text": k, "value": v} for k, v in self.STATS_DICT.items()],
            v_model="mean",
        )

        self.w_cores = v.Slider(
            v_model=cpu_count(),
            thumb_label="Always",
            step=1,
            label="Processors",
            min=1,
            max=cpu_count(),
        )

        self.w_chunk = v.Slider(
            v_model=200,
            thumb_label="Always",
            step=20,
            label="Chunk size",
            max=1000,
            min=20,
        )

        advanced_settings = v.ExpansionPanels(
            flat=False,
            children=[
                v.ExpansionPanel(
                    children=[
                        v.ExpansionPanelHeader(children=["Advanced settings"]),
                        v.ExpansionPanelContent(children=[self.w_cores, self.w_chunk]),
                    ],
                ),
            ],
        )

        self.children = [
            v.Subheader(children=["Area selection"]),
            v.Divider(),
            self.w_selector,
            v.Subheader(children=["Date selection"]),
            v.Divider(),
            self.date_selector,
            v.Divider(),
            self.w_stats,
            advanced_settings,
            self.btn,
            self.alert,
            self.output,
        ]

        link((self.w_stats, "items"), (self.model, "items"))
        link((self.w_stats, "v_model"), (self.model, "selected"))
        link((self.w_cores, "v_model"), (self.model, "cores"))
        link((self.w_chunk, "v_model"), (self.model, "chunks"))

        self.btn.on_event("click", self.on_click)
        self.w_selector.w_field.observe(self.field_change, "v_model")

    @su.loading_button()
    def on_click(self, widget, event, data):

        with self.output:
            self.output.clear_output()
            stackstat.stack_composed(
                self.w_selector, self.date_selector, self.model, self.alert
            )

    def field_change(change, date_selector, alert):
        alert.clear()

        months_and_years = get_months_years(w_selector.get_current_path(), alert)

        if months_and_years:
            years, months = months_and_years
        else:
            # Stop the excecution
            return
        date_selector.clear_season()

        parsed_months = date_selector.numbers_to_months(months)
        date_selector.months_items = parsed_months
        date_selector.years_items = years

    def get_months_years(self, path, alert):

        """From a given path of images, the function will return a list
        of the months/years present in the folder

        """

        tifs = Path(path).glob("*.tif")

        if tifs:
            try:
                years = list(
                    set([ps.parse_other_files(image)[4].year for image in tifs])
                )
                months = list(
                    set([ps.parse_other_files(image)[4].month for image in tifs])
                )
                years.sort()
                months.sort()

                return years, months
            except Exception as e:
                alert.add_msg(
                    "ERROR: Check the folder and make sure that \
                    all the images follow the format: 'YYYY_mm_dd'",
                    type_="error",
                )

                return None
        else:
            alert.add_msg(
                "ERROR: The folder is empty. Please make sure that you \
                have run the closing filter before run the statistics.",
                type_="error",
            )

    def get_stat_as_parameter(self):
        """Convert the selected stat as the input to the stack-composed script"""

        return self.STATS_DICT[self.selected]
