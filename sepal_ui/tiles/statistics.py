#!/usr/bin/env python3

from os import cpu_count
from glob import glob
from functools import partial 

from traitlets import HasTraits, List, link, Unicode, Int
from ipywidgets import Output, HTML
import ipyvuetify as v


import modules.stackcomposed.stack_composed.parse as ps
from .dateselector import DateSelector, date_picker_tile

from sepal_ui import sepalwidgets as s

from scripts.stackstat import stack_composed

statistics_text = HTML("""
<p>After the data is filtered, a time series analysis of the soil 
moisture maps can be performed. Several statistics can be applied 
whether to the entire time series or to a specified range, 
statistics as median, mean, standard deviation or linear 
trend (slope of the line) are available to process the selected data.</p>

<p>This module uses the <a href='https://github.com/SMByC/StackComposed' target='_blank'>
Stack Composed python module</a>, which was developed by the SMByC of Ideam (Colombia), 
that computes a specific statistic for all valid pixel values across the time 
series using a parallel process. </p>

<p>There are three options for analyzing the data for 
different time frames.</p>

<ul>
<li><b>All time series</b>: runs the analysis for all the 
images in the given folder.</li>
<li><b>Range</b>: runs the analysis for all the images within 
the time frame selected.</li>
<li><b>Season</b>: the user can define a season by selecting months or years.
The analysis is run for only the years/months selected. 
For example if January, February and 2016, 2017, 2018 are selected, 
then the analysis would run for January 2016, 
January 2017, January 2018,  February 2016, February 2017 and February 2018.
If only a month is selected (without years), the analysis would run all the 
years for the given month.</li>
""")

def get_months_years(path, alert):
    
    """ From a given path of images, the function will return a list 
    of the months/years present in the folder
    
    """

    tifs = glob(f'{path}/*.tif')

    if tifs:
        try:
            years = list(set([ps.parse_other_files(image)[4].year for image in tifs]))
            months = list(set([ps.parse_other_files(image)[4].month for image in tifs]))
            years.sort()
            months.sort()

            return years, months

        except Exception as e:
            alert.add_msg("ERROR: Check the folder and make sure that \
                all the images follow the format: 'YYYY_mm_dd'", type_='error')

            return None
    else:
        alert.add_msg("ERROR: The folder is empty. Please make sure that you \
            have run the closing filter before run the statistics.", type_='error')


class Statistics(HasTraits):

    STATS_DICT = {'Median' : 'median',
        'Mean' : 'mean',
        'Geometric mean' : 'Gmean',
        'Maximum' : 'max',
        'Minimum' : 'min',
        'Standard deviation' : 'std',
        'Valid pixels' : 'valid_pixels',
        'Linear trend' : 'linear_trend'
    }

    items = List().tag(sync=True)
    selected = Unicode().tag(sync=True)
    cores = Int().tag(sync=True)
    chunks = Int(200).tag(sync=True)

    def __init__(self):
        
        self.items = self.get_stats()
        self.selected = self.get_first_stat()
        self.cores = self.get_cores()

        
    def get_stats(self):

        return list(self.STATS_DICT.keys())

    def get_first_stat(self):

        return self.get_stats()[0]

    def get_not_null_attrs(self):
        """Returns a dictionary with non-null attributes

        """
        return dict((k, v) for k, v in self.__dict__.items() if v is not None)

    def get_cores(self):
        cores = cpu_count()

        return cores

    def get_stat_as_parameter(self):
        """ Convert the selected stat as the input to the stack-composed script

        """

        return self.STATS_DICT[self.selected]



def statistics_tile(w_selector, statistics_io):

    def on_click(widget, 
        event, 
        data, 
        path_selector, 
        date_selector, 
        statistic, 
        alert, 
        out):
    
        # Clear output if there is something printed before
        out.clear_output()

        # Once the button is clicked, disable it
        btn.disable()

        # Clear old alert messages
        alert.clear()

        @out.capture() 
        def run_process(path_selector, date_selector, statistic, alert):

            stack_composed(
                path_selector,
                date_selector,
                statistic,
                alert
        )

        run_process(path_selector, date_selector, statistic, alert)

        # Reactivate button
        btn.activate()


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

    alert = s.Alert()
    btn = s.Btn(text="Calculate statistics")
    out = Output()
    date_selector = DateSelector(season=True, remove_method=['Single date']) 

    field_widget = w_selector.children[1]
    field_widget.observe(partial(field_change, date_selector=date_selector, alert=alert), 'v_model')


    date_tile = date_picker_tile(date_selector)

    w_stats = v.Select(
        label='Statistic',
        items = statistics_io.items,
        v_model=statistics_io.selected,
    )

    link((w_stats, 'items'), (statistics_io, 'items'))
    link((w_stats, 'v_model'), (statistics_io, 'selected'))
    


    w_cores = v.Slider(v_model=statistics_io.cores, thumb_label='Always', step=1, label='Processors', min=1, max=statistics_io.cores)
    link((w_cores, 'v_model'),(statistics_io, 'cores'))

    w_chunk = v.Slider(v_model=200, thumb_label='Always', step=20, label='Chunk size', max=1000, min=20)
    link((w_chunk, 'v_model'),(statistics_io, 'chunks'))


    advanced_settings = v.ExpansionPanels(flat=False, children=[
    v.ExpansionPanel(
        children=[
            v.ExpansionPanelHeader(children=['Advanced settings']),
            v.ExpansionPanelContent(children=[w_cores, w_chunk])
        ],
    ),
    ])


    btn.on_event('click', partial(
        on_click,
        path_selector=w_selector,
        date_selector=date_selector,
        statistic=statistics_io,
        alert=alert,
        out=out,
    ))

    content = v.Layout(
        dark=True, 
        _metadata={'mount-id': 'data-input'},
        class_="pa-5",
        row=True,
        align_center=True, 
        children=[
            v.Flex(xs12=True, children=[
                statistics_text,
                v.Subheader(children=['Area selection']),
                v.Divider(),
                w_selector,
                v.Subheader(children=['Date selection']),
                v.Divider(),
                date_tile,
                v.Divider(),
                w_stats,
                advanced_settings,
                btn,
                alert,
                out
                ]
            ),
        ]
    )

    return content