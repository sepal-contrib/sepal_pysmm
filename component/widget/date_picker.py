from datetime import datetime
from typing import Optional

import ipyvuetify as v
import sepal_ui.sepalwidgets as sw
import traitlets as t
from traitlets import link, observe

__all__ = ["DatePicker"]


class DatePicker(sw.Layout):
    menu: Optional[v.Menu] = None
    "the menu widget to display the datepicker"

    date_text: Optional[v.TextField] = None
    "the text field of the datepicker widget"

    disabled: t.Bool = t.Bool(False).tag(sync=True)
    "the disabled status of the Datepicker object"

    def __init__(self, label: str = "Date", layout_kwargs: dict = {}, **kwargs) -> None:
        """
        Input widget to provide a reusable DatePicker.

        It allows to choose date as a string in the following format YYYY-MM-DD.

        Args:
        ----
            label: the label of the datepicker field
            layout_kwargs: any parameter for the wrapper v.Layout
            kwargs: any parameter from a v.DatePicker object.
        """
        kwargs["v_model"] = kwargs.get("v_model", "")

        # create the widgets
        self.date_picker = v.DatePicker(no_title=True, scrollable=True, **kwargs)

        self.date_text = v.TextField(
            label=label,
            hint="YYYY-MM-DD format",
            persistent_hint=True,
            prepend_icon="event",
            readonly=True,
            v_on="menuData.on",
        )

        self.menu = v.Menu(
            min_width="290px",
            transition="scale-transition",
            offset_y=True,
            v_model=False,
            close_on_content_click=False,
            children=[self.date_picker],
            v_slots=[
                {
                    "name": "activator",
                    "variable": "menuData",
                    "children": self.date_text,
                }
            ],
        )

        # set the default parameter
        layout_kwargs = {}
        layout_kwargs.setdefault("row", True)
        layout_kwargs.setdefault("class_", "pa-5")
        layout_kwargs.setdefault("align_center", True)
        layout_kwargs.setdefault("children", [v.Flex(xs10=True, children=[self.menu])])

        # call the constructor
        super().__init__(**layout_kwargs)

        link((self.date_picker, "v_model"), (self.date_text, "v_model"))
        link((self.date_picker, "v_model"), (self, "v_model"))

    @observe("v_model")
    def check_date(self, change: dict) -> None:
        """
        Check if the data is formatted date.

        A method to check if the value of the set v_model is a correctly formated date
        Reset the widget and display an error if it's not the case.
        """
        self.date_text.error_messages = None

        # exit immediately if nothing is set
        if not change["new"]:
            return

        # change the error status
        if not self.is_valid_date(change["new"]):
            msg = self.date_text.hint
            self.date_text.error_messages = msg

        return

    @observe("v_model")
    def close_menu(self, change: dict) -> None:
        """Close the menu of the datepicker programatically."""
        # set the visibility
        self.menu.v_model = False

        return

    @observe("disabled")
    def disable(self, change: dict) -> None:
        """Disable the appropriate components in the datipkcer object."""
        self.menu.v_slots[0]["children"].disabled = self.disabled

        return

    @staticmethod
    def is_valid_date(date: str) -> bool:
        """
        Check if the date is provided using the date format required for the widget.

        Args:
        ----
            date: the date to test in YYYY-MM-DD format
        Returns:
            the date to test.
        """
        try:
            datetime.strptime(date, "%Y-%m-%d")
            valid = True

        except Exception:
            valid = False

        return valid
