from traitlets import Unicode, List, link
from ipywidgets.widgets.trait_types import Date, date_serialization
import ipyvuetify as v
import sepal_ui.sepalwidgets as sw
import sepal_ui.scripts.utils as su


class DateSelector(v.Layout):

    date_method = Unicode(None, allow_none=True).tag(sync=True)
    single_date = Unicode(None, allow_none=True).tag(sync=True)
    
    start_date = Unicode(None, allow_none=True).tag(sync=True)
    end_date = Unicode(None, allow_none=True).tag(sync=True)

    years_items = List(allow_none=True).tag(sync=True)
    months_items = List(allow_none=True).tag(sync=True)
    selected_years = List(allow_none=True).tag(sync=True)
    selected_months = List(allow_none=True).tag(sync=True)

    MONTHS_DICT = {
        1: "january",
        2: "february",
        3: "march",
        4: "april",
        5: "may",
        6: "june",
        7: "july",
        8: "august",
        9: "september",
        10: "october",
        11: "november",
        12: "december",
    }

    SELECTION_METHODS = [
        {"text": "Single date", "value": "single"},
        {"text": "Range", "value": "range"},
        {"text": "All time series", "value": "all"},
    ]

    def __init__(
        self,
        *args,
        season=False,
        remove_method=[],
        years_items=[],
        months_items=[],
        **kwargs,
    ):

        self.align_center = True
        self.class_ = "d-block pa-2"
        super().__init__(*args, **kwargs)

        self._metadata = {"mount-id": "data-input"}

        # Selector date method
        self.w_date_method = v.Select(
            v_model="",
            label="Specify the selection date method",
            items=self.SELECTION_METHODS,
        )

        if remove_method:
            new_items = []
            for to_remove in remove_method:
                new_items += [
                    method
                    for method in self.SELECTION_METHODS
                    if to_remove not in method["value"]
                ]
            if not new_items:
                raise ValueError(f"The selected method does not exist")
            self.w_date_method.items = new_items
        if season:
            self.w_date_method.items = list(
                self.w_date_method.items + [{"text": "Season", "value": "season"}]
            )[:]
        self.w_unique_date = sw.DatePicker(
            label="Date",
        ).hide()

        self.w_ini_date = sw.DatePicker(label="Start date").hide()
        self.w_end_date = sw.DatePicker(label="End date").hide()
        self.w_mmonths = v.Select(
            multiple=True,
            chips=True,
            label="Months",
            deletable_chips=True,
            v_model=self.selected_months,
            items=self.months_items,
        )
        self.w_myears = v.Select(
            multiple=True,
            chips=True,
            label="Years",
            deletable_chips=True,
            v_model=self.selected_years,
            items=self.years_items,
        )

        link((self.w_date_method, "v_model"), (self, "date_method"))
        link((self.w_end_date, "v_model"), (self, "end_date"))
        link((self.w_ini_date, "v_model"), (self, "start_date"))
        link((self.w_unique_date, "v_model"), (self, "single_date"))
        link((self.w_mmonths, "items"), (self, "selected_months"))
        link((self.w_myears, "items"), (self, "selected_years"))
        link((self.w_mmonths, "items"), (self, "months_items"))
        link((self.w_myears, "items"), (self, "years_items"))

        self.children = [
            self.w_date_method,
            self.w_unique_date,
            v.Flex(children=[self.w_ini_date, self.w_end_date]),
            self.w_myears,
            self.w_mmonths,
        ]
        self.display_elements({"new": None})
        self.w_date_method.observe(self.display_elements, "v_model")

    def display_elements(self, change):

        widgets = ["w_unique_date", "w_ini_date", "w_end_date", "w_mmonths", "w_myears"]
        
        

        # Hide all
        for widget in widgets:
            su.hide_component(getattr(self, widget))
        if change["new"] == "single":
            su.show_component(self.w_unique_date)
        elif change["new"] == "range":
            su.show_component(self.w_end_date)
            su.show_component(self.w_ini_date)
        elif change["new"] == "season":
            su.show_component(self.w_mmonths)
            su.show_component(self.w_myears)

    def numbers_to_months(self, number_list):

        """From a given list of numbers, the function will return a list of
        parsed months"""

        parsed_months = [self.MONTHS_DICT[key].capitalize() for key in number_list]

        return parsed_months

    def months_to_numbers(self):

        """From a given list of string months, the function will return a list of
        parsed integer months"""

        # Invert dictionary
        inverted_dict = {v: k for k, v in self.MONTHS_DICT.items()}

        parsed_numbers = [inverted_dict[key.lower()] for key in self.selected_months]

        return parsed_numbers
