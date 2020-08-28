#!/usr/bin/env python3

import sys
sys.path.append('..')

from functools import partial

from traitlets import HasTraits, Unicode, List, link
import ipywidgets as widgets
from ipywidgets.widgets.trait_types import Date, date_serialization

import ipyvuetify as v


from sepal_ui import widgetBinding as wb
from sepal_ui import sepalwidgets as s

class DateSelector(HasTraits):
    """ Selected dates objects

    """
    date_method = Unicode().tag(sync=True)
    single_date = Date(None).tag(sync=True, **date_serialization)
    start_date = Date(None).tag(sync=True, **date_serialization)
    end_date = Date(None).tag(sync=True, **date_serialization)

    years_items = List().tag(sync=True)
    months_items = List().tag(sync=True)
    selected_years = List().tag(sync=True)
    selected_months = List().tag(sync=True)

    MONTHS_DICT = {

            1:'january', 2:'february',
            3:'march', 4:'april',
            5:'may', 6:'june',
            7:'july', 8:'august',
            9:'september', 10:'october',
            11:'november', 12:'december'
    }

    def __init__(self, season=False, remove_method=[], years_items=[], months_items=[]):

        """
        Args: 
            season (boolean) optional: If true, add the season method.
            remove_method (list): Selection method to remove from the selectable list

        """
        self.months_items = months_items
        self.years_items = years_items

        self.selection_methods = sorted(['Single date', 'Range', 'All time series'])

        if season:
            self.selection_methods.append('Season')

        if all(method in self.selection_methods for method in remove_method):
            self.selection_methods = list(set(self.selection_methods)^set(remove_method))
        else:
            raise ValueError(f'The selected method does not exist')

    def get_not_null_attrs(self):
        """Returns a dictionary with non-null attributes

        """
        return dict((k, v) for k, v in self.__dict__.items() if v is not None)

    def clear_dates(self):
        """ When the method is called, clean the object attributes.

        """
        self.single_date = None
        self.start_date = None
        self.end_date = None


    def clear_season(self):

        self.years_items = []
        self.months_items = []
        self.selected_years = []
        self.selected_months = []

    def numbers_to_months(self, number_list):
        
        """ From a given list of numbers, the function will return a list of 
        parsed months"""
        
        parsed_months = [self.MONTHS_DICT[key].capitalize() for key in number_list]
        
        return parsed_months

    def months_to_numbers(self):
        
        """ From a given list of string months, the function will return a list of 
        parsed integer months """
        
        # Invert dictionary
        inverted_dict = {v : k for k, v in self.MONTHS_DICT.items()}

        parsed_numbers = [inverted_dict[key.lower()] for key in self.selected_months]
        
        return parsed_numbers

def date_picker_tile(Dates):

    import ipywidgets as widgets
    
    def bind_change(change, obj, attr):
        setattr(obj, attr, change['new'])

    # Date unique widget
    w_unique_date = widgets.DatePicker(
        description='Date',
    )
    w_unique_cont = v.Container(
        class_='pa-5 d-none', 
        children=[
            w_unique_date
        ]

    )
    # Create two-way-binding with Dates object
    link((w_unique_date, 'value'), (Dates, 'single_date'))

    # Date range widget
    w_ini_date = widgets.DatePicker(
        description='Start date',
    )
    w_ini_date_cont = v.Container(
        class_='pa-5 d-none', 
        children=[
            w_ini_date
        ]
    )
    link((w_ini_date, 'value'), (Dates, 'start_date'))


    w_end_date = widgets.DatePicker(
        description='End date',
    )
    w_end_date_cont = v.Container(
        class_='pa-5 d-none', 
        children=[
            w_end_date
        ]
    )
    link((w_end_date, 'value'), (Dates, 'end_date'))

    # Season pickerr

    w_mmonths = v.Select(
        class_='d-none',
        multiple=True, 
        chips=True, 
        label='Months', 
        deletable_chips=True, 
        v_model=Dates.selected_months,
        items=Dates.months_items,
    )

    link((w_mmonths, 'v_model'), (Dates, 'selected_months'))
    link((w_mmonths, 'items'), (Dates, 'months_items'))


    w_myears = v.Select(
        class_='d-none',
        multiple=True, 
        chips=True, 
        label='Years', 
        deletable_chips=True, 
        v_model=Dates.selected_years,
        items=Dates.years_items,
    )

    link((w_myears, 'v_model'), (Dates, 'selected_years'))
    link((w_myears, 'items'), (Dates, 'years_items'))


    # Selector date method
    w_date_method = v.Select(
        v_model='',
        label='Specify the selection date method', 
        items=Dates.selection_methods
    )
    
    # Bind the selected value to the object
    link((w_date_method, 'v_model'), (Dates, 'date_method'))


    widgets = [w_unique_cont, w_ini_date_cont, w_end_date_cont, w_mmonths, w_myears]

    # Create a behavior after change the clicked value of w_date_method
    wb.bind_dates(w_date_method, widgets, Dates)

    dates_content = v.Layout(
        _metadata={'mount-id': 'data-input'},
        class_="pa-5",
        row=True,
        align_center=True, 
        children=[
            v.Flex(xs12=True, children=[w_date_method]),
            v.Flex(xs12=True, children=[w_unique_cont]),
            v.Flex(xs12=True, children=[
                v.Layout(class_='flex-column', children=[
                    v.Flex(
                        children=[
                            w_ini_date_cont, 
                            w_end_date_cont
                        ])
                    ]
                )
            ]),
            v.Flex(xs12=True, children=[
                v.Layout(class_='flex-column', children=[
                    v.Flex(
                        children=[
                            w_myears,
                            w_mmonths, 
                        ])
                    ]
                )
            ])
        ]
    )

    return dates_content

