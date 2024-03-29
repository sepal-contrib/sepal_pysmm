import ipyvuetify as v
import sepal_ui.sepalwidgets as sw
from traitlets import List, Unicode, link

from component.widget.date_picker import DatePicker


class DateSelector(sw.Layout):
    date_method = Unicode(None, allow_none=True).tag(sync=True)
    single_date = Unicode(None, allow_none=True).tag(sync=True)

    start_date = Unicode(None, allow_none=True).tag(sync=True)
    end_date = Unicode(None, allow_none=True).tag(sync=True)

    years_items = List(allow_none=True).tag(sync=True)
    months_items = List(allow_none=True).tag(sync=True)

    selected_years = List(allow_none=True).tag(sync=True)
    selected_months = List(allow_none=True).tag(sync=True)

    SELECTION_METHODS = [
        {"text": "All time series", "value": "all"},
        {"text": "Range", "value": "range"},
        {"text": "Single date", "value": "single"},
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
            items=self.SELECTION_METHODS[1:],
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
                raise ValueError("The selected method does not exist")
            self.w_date_method.items = new_items

        if season:
            self.w_date_method.items = list(
                [*self.w_date_method.items, {"text": "Season", "value": "season"}]
            )[:]

        self.w_unique_date = DatePicker(
            label="Date", attributes={"id": "unique_date"}
        ).hide()
        self.w_ini_date = DatePicker(
            label="Start date", attributes={"id": "ini_date"}
        ).hide()
        self.w_end_date = DatePicker(
            label="End date", attributes={"id": "end_date"}
        ).hide()

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
        link((self.w_mmonths, "v_model"), (self, "selected_months"))
        link((self.w_myears, "v_model"), (self, "selected_years"))
        link((self.w_mmonths, "items"), (self, "months_items"))
        link((self.w_myears, "items"), (self, "years_items"))

        self.children = [
            self.w_date_method,
            self.w_unique_date,
            v.Flex(class_="d-flex", children=[self.w_ini_date, self.w_end_date]),
            self.w_myears,
            self.w_mmonths,
        ]
        self.display_elements({"new": None})
        self.w_date_method.observe(self.display_elements, "v_model")

    def display_elements(self, change):
        widgets = ["w_unique_date", "w_ini_date", "w_end_date", "w_mmonths", "w_myears"]

        # Hide all
        for widget in widgets:
            getattr(self, widget).hide()

        if change["new"] == "single":
            self.w_unique_date.show()

        elif change["new"] == "range":
            self.w_end_date.show()
            self.w_ini_date.show()

        elif change["new"] == "season":
            self.w_mmonths.show()
            self.w_myears.show()
