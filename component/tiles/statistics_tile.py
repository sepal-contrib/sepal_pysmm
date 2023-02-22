from os import cpu_count
from pathlib import Path
import re
import datetime

from traitlets import link, dlink
from ipywidgets import Output
import ipyvuetify as v
import sepal_ui.sepalwidgets as sw
import sepal_ui.scripts.utils as su

import component.parameter as param
import component.widget as cw
from component.message import cm
import component.scripts as cs


__all__ = ["StatisticsTile"]


class StatisticsTile(v.Layout, sw.SepalWidget):
    def __init__(self, model, *args, **kwargs):

        self.class_ = "d-block"
        self._metadata = {"mount_id": "statistics"}

        super().__init__(*args, **kwargs)
        
        self.model = model

        self.inputs_view = StatsInputView(model=self.model)
        self.statistics_view = StatisticsView(model=self.model)

        views = [self.inputs_view, self.statistics_view]

        titles = ["Inputs", "Process"]

        self.children = [
            v.Card(
                class_="mb-2",
                children=[
                    v.CardTitle(children=[sw.Markdown(cm.statistics_tile.title)]),
                    v.CardText(children=[sw.Markdown(cm.statistics_tile.desc)]),
                ],
            )
        ] + [
            v.Card(class_="pa-2 mb-2", children=[v.CardTitle(children=[title]), card])
            for card, title in zip(*[views, titles])
        ]


class StatsInputView(sw.Layout):
    def __init__(self, model, *args, **kwargs):

        self.class_ = "d-flex"

        super().__init__(*args, **kwargs)

        self.model = model

        self.w_selector_view = cw.FolderSelectorView(
            folder=param.PROCESSED_DIR.parent, wildcard="close*.tif"
        )
        self.w_selector = self.w_selector_view.w_selector
        self.btn = sw.Btn("View images", class_="mb-2", small=True)
        self.alert = sw.Alert()

        self.date_selector = cw.DateSelector(season=True, remove_method=["single"])
        self.date_selector.date_method = "all"

        self.close = v.Icon(children=["mdi-close"], small=True)
        self.w_summary = v.Dialog(
            max_width=800, 
            min_width=800, 
            min_height=450,
            max_height=450, 
            v_model=False,
            style_="overflow: hidden;",
            close_on_back=True,
            close_on_content_click=True,
            children=[
                sw.Card(
                    style_="overflow: hidden;",
                    children=[
                        sw.CardTitle(
                            class_="pa-0 ma-0", 
                            children=[v.Spacer(), self.close]
                        ),
                        sw.CardText(children=[], attributes={"id":"summary_card"}),
                    ]
                )
            ]
        )

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
                                    v.CardTitle(children=["Date selection"]),
                                    self.date_selector,
                                    self.btn,
                                    self.w_summary,
                                    self.alert
                                ]
                            )
                        ]
                    ),
                ]
            ),
        ]

        self.model.bind(self.w_selector_view.w_recursive, "recursive").bind(
            self.w_selector, "folders"
        )


        dlink((self.date_selector, "date_method"), (self.model, "date_method"))
        dlink((self.date_selector, "start_date"), (self.model, "start_date"))
        dlink((self.date_selector, "end_date"), (self.model, "end_date"))
        dlink((self.date_selector, "selected_years"), (self.model, "selected_years"))
        dlink((self.date_selector, "selected_months"), (self.model, "selected_months"))

        self.w_selector.observe(self.fill_season, "v_model")
        self.w_selector.v_model

        self.btn.on_event("click", self.get_list_of_images)
        self.close.on_event("click", lambda *args: setattr(self.w_summary, "v_model", False))

    @su.loading_button(debug=True)
    def get_list_of_images(self, *args):
        """Display the list of images filtered by the date selector on a dialog"""
            
        filter_images, _ = self.model.get_inputs()
        summary = cs.images_summary(filter_images)

        self.get_children(id_="summary_card")[0].children = [
            cw.VueDataFrame(data=summary, title="Selected Images")
        ]

        setattr(self.w_summary, "v_model", True)


    def fill_season(self, change):
        """Fill years and months when Season is Selected, receive a list of paths"""

        months, years = self.get_months_years(change["new"])

        month_items = [
            {"text": text, "value": value}
            for value, text in param.MONTHS_DICT.items()
            if value in months
        ]

        self.date_selector.months_items = month_items
        self.date_selector.years_items = years

        selected_months = [month["value"] for month in month_items]

        self.date_selector.selected_months = selected_months
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

        match = re.search(r"\d{4}_\d{2}_\d{2}", filename)
        if match:

            date = datetime.datetime.strptime(match.group(), "%Y_%m_%d").date()
            jday = date.timetuple().tm_yday

            return date


class StatisticsView(v.Layout):

    STATS_DICT = {
        "Median": "median",
        "Mean": "mean",
        "Geometric mean": "gmean",
        "Maximum": "max",
        "Minimum": "min",
        "Standard deviation": "std",
        "Valid pixels": "valid_pixels",
        "Linear trend": "linear_trend",
    }

    def __init__(self, model, *args, **kwargs):

        self.class_ = "d-block"

        super().__init__(*args, **kwargs)

        self.model = model

        self.alert = sw.Alert()
        self.btn = sw.Btn("Get stack", class_="mr-2")
        self.output = Output()


        self.w_stats = v.Select(
            label="Statistic",
            items=[{"text": k, "value": v} for k, v in self.STATS_DICT.items()],
            v_model="mean",
        )

        self.w_prefix = v.TextField(
            label="Create a suffix for the output",
            v_model=self.model.prefix,
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
            class_="mb-3",
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
            self.w_stats,
            self.w_prefix,
            advanced_settings,
            v.Flex(class_="d-flex mb-2", children=[self.btn]),
            self.alert,
            self.output,
        ]

        self.model.bind(self.w_stats, "items").bind(self.w_stats, "selected_stat").bind(
            self.w_cores, "cores"
        ).bind(self.w_chunk, "chunks").bind(self.w_prefix, "prefix")

        self.btn.on_event("click", self.on_click)

    @su.loading_button(debug=True)
    def on_click(self, *args):

        filter_images, output_name = self.model.get_inputs()

        self.alert.add_msg(
            f"Executing {self.model.selected_stat} for {len(filter_images)} images..."
        )

        # Create a file with the selected images
        tmp_tif_file = param.STACK_DIR / "tmp_images.txt"
        tmp_tif_file.write_text("\n".join(filter_images))

        with self.output:
            self.output.clear_output()
            self.model.stack_composed(str(tmp_tif_file), str(output_name))

        # Once the process has ran remove the tmp_tif_file
        tmp_tif_file.unlink()

        self.alert.add_msg(
            f"Done! results saved in {output_name.parent}"
        )
