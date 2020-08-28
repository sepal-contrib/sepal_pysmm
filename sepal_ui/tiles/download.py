#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from modules.ipyfilechooser import FileChooser
import getpass
from functools import partial 
import ipywidgets as widgets
import ipyvuetify as v

from sepal_ui import sepalwidgets as s
from sepal_ui import widgetBinding as wb



class Download:

    overwrite = True
    rmdrive = True
    tasks_file_name = ''


def download_tile(obj):

    def bind_change(change, obj, attr):
        setattr(obj, attr, change['new'])

    def bind_fc(fc, obj, attr):
        setattr(obj, attr, fc.selected)


    #File chooser

    user = getpass.getuser()

    fc = FileChooser(f'/home/{user}/')
    fc.register_callback(partial(bind_fc, fc=fc, obj=obj, attr='tasks_file_name'))

    w_overwrite = v.Switch(v_model=obj.overwrite, inset=True, label="Overwrite SEPAL images")
    w_overwrite.observe(partial(bind_change, obj=obj, attr='overwrite'), 'v_model')

    w_remove = v.Switch(v_model=obj.rmdrive, inset=True, label="Remove Google Drive Images")
    w_remove.observe(partial(bind_change, obj=obj, attr='rmdrive'), 'v_model')

    out = widgets.Output()
    btn = s.Btn(text="Download", icon='download')

    # Create an alert element for the process
    process_alert = s.Alert()

    wb.bin_download_process(obj, btn, out, process_alert)

    html_header = """
    <style>
    .widget-html span {
        color:black!important;
    }
    div.output_stderr{
        color:none;
    }
    </style>
    <p>With this module you can track and download the images processed into your Google Earth Engine account 
    by providing the 'tasks' text file, the results will be stored directly into your SEPAL account.</br>
    <b>Note that if you check the overwrite and remove options, the result can't be undone.</b>
    </p>
    """

    download_content = v.Layout(

        class_="pa-5",
        row=True,
        align_center=True, 
        children=[
            v.Flex(xs12=True, children=[
                v.Sheet(class_="pa-5",
                    children=[
                        widgets.HTML(html_header),
                        fc,
                        w_overwrite,
                        w_remove,
                        btn,
                        process_alert,
                        out,
                    ]
                )
            ])
        ]
    )

    return download_content