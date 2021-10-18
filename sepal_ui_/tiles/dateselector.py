#!/usr/bin/env python3

import sys

sys.path.append("..")

from functools import partial

from traitlets import HasTraits, Unicode, List, link
import ipywidgets as widgets
from ipywidgets.widgets.trait_types import Date, date_serialization

import ipyvuetify as v


from sepal_ui import widgetBinding as wb
from sepal_ui import sepalwidgets as s


class DateSelector(HasTraits):
    """Selected dates objects"""

    def __init__(
        self,
    ):

        """
        Args:
            season (boolean) optional: If true, add the season method.
            remove_method (list): Selection method to remove from the selectable list

        """
        self.months_items = months_items
        self.years_items = years_items

        self.selection_methods = sorted(["Single date", "Range", "All time series"])

        if season:
            self.selection_methods.append("Season")

        if all(method in self.selection_methods for method in remove_method):
            self.selection_methods = list(
                set(self.selection_methods) ^ set(remove_method)
            )
        else:
            raise ValueError(f"The selected method does not exist")

    def get_not_null_attrs(self):
        """Returns a dictionary with non-null attributes"""
        return dict((k, v) for k, v in self.__dict__.items() if v is not None)

    def clear_dates(self):
        """When the method is called, clean the object attributes."""
        self.single_date = None
        self.start_date = None
        self.end_date = None

    def clear_season(self):

        self.years_items = []
        self.months_items = []
        self.selected_years = []
        self.selected_months = []
