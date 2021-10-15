from os import cpu_count
from pathlib import Path
import re
import datetime

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

        self.w_selector_view = cw.FolderSelectorView(folder=param.PROCESSED_DIR.parent, max_depth=0)
        
        self.w_selector = self.w_selector_view.w_selector

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
            v.Row(
                children=[
                    v.Col(
                        children=[
                            v.CardTitle(children=["Folder selection"]),
                            self.w_selector_view,
                        ]
                    ),
                    v.Col(
                        children=[
                            v.CardTitle(children=["Date selection"]),
                            self.date_selector,
                        ]
                    ),
                ]
            ),
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
        self.w_selector.observe(self.fill_season, "v_model")

    @su.loading_button()
    def on_click(self, widget, event, data):

        with self.output:
            self.output.clear_output()
            stackstat.stack_composed(
                self.w_selector, self.date_selector, self.alert
            )

    def fill_season(self, change):
        """Fill years and months when Season is Selected"""
        
            
        months, years = self.get_months_years(change["new"])
        parsed_months = self.date_selector.numbers_to_months(months)

        self.date_selector.months_items = parsed_months
        self.date_selector.years_items = years

        self.date_selector.selected_months = parsed_months
        self.date_selector.selected_years = years
            
    
    def get_months_years(self, path):

        """From a given path of images, the function will return a list
        of the months/years present in the folder

        """
        
        if self.w_selector_view.w_recursive.v_model:
            tifs = [tif for folder in path for tif in Path(folder).rglob("[!.]*.tif")]
        else:
            tifs = [tif for folder in path for tif in Path(folder).glob("[!.]*.tif")]
        
        dates = [date for date in [self.get_date(image) for image in tifs] if date]
        
        years = sorted(list(set(date.year for date in dates)))
        months = sorted(list(set(date.month for date in dates)))
        
        return months, years
        
    @staticmethod
    def get_date(image_path):
        """
        Parse the date of the images

        Examples:
            close_SMCmap_2019_11_09_dguerrero_1111.tif
        """
        filename = Path(image_path).stem

        match = re.search(r'\d{4}_\d{2}_\d{2}', filename) 
        if match:

            date = datetime.datetime.strptime(match.group(), '%Y_%m_%d').date()
            jday = date.timetuple().tm_yday

            return date

    def get_stat_as_parameter(self):
        """Convert the selected stat as the input to the stack-composed script"""

        return self.STATS_DICT[self.selected]
