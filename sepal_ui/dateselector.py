#!/usr/bin/env python3

import sys
sys.path.append('..')

from traitlets import HasTraits, link
import ipywidgets as widgets
from ipywidgets.widgets.trait_types import Date, date_serialization

import ipyvuetify as v


from sepal_ui import widgetBinding as wb
from sepal_ui import widgetFactory as wf
from sepal_ui import sepalwidgets as s

class SelectedDates(HasTraits):
    """ Selected dates objects

    """

    single_date = Date(None).tag(sync=True, **date_serialization)
    start_date = Date(None).tag(sync=True, **date_serialization)
    end_date = Date(None).tag(sync=True, **date_serialization)

    def __init__(self):

        self.date_method = None

        # Single_date can be used for single date method
        # or as the first date in a range



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

    # Selector date method

    w_date_method = v.Select(
        v_model=None,
        label='Retrieve date method', 
        items=['Single date', 'Range', 'All time series']
    )
    
    # Bind the selected value to the object
    w_date_method.observe(partial(bind_change, obj=Dates, attr='date_method'), 'v_model')


    widgets = [w_unique_cont, w_ini_date_cont, w_end_date_cont]

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
            ])
        ]
    )

    return dates_content

