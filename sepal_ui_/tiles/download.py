#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import getpass
from functools import partial
import ipywidgets as widgets
import ipyvuetify as v

from sepal_ui import sepalwidgets as s
from sepal_ui import widgetBinding as wb
from scripts import download_to_sepal


class Download:

    overwrite = True
    rmdrive = True


def on_download(obj, w_selector, btn, out, alert):
    """Starts the download process.

    Args:
        obj (Download): Download object
        w_selector (w_selector): Widget selector
        btn (Trigger Button): Button to trigger the callback
        out (widgets.out): Widget area to capture outputs
        process_alert (s.Alert): Alert to display useful messages
    """

    def on_click(widget, event, data, out, obj, alert, w_selector):

        task_file_name = w_selector.get_file_path()
        overwrite = obj.overwrite
        rmdrive = obj.rmdrive

        # Clear output if there is something printed before
        out.clear_output()

        # Once the button is clicked, disable it
        btn.disable()

        # Clear old alert messages
        alert.clear()

        @out.capture()
        def run_process(obj):
            download_to_sepal.run(
                task_file_name,
                alert,
                overwrite=overwrite,
                rmdrive=overwrite,
            )

        run_process(obj)
        btn.activate()

    btn.on_event(
        "click",
        partial(
            on_click,
            obj=obj,
            out=out,
            alert=alert,
            w_selector=w_selector,
        ),
    )


def download_tile(obj, w_selection):
    def bind_change(change, obj, attr):
        setattr(obj, attr, change["new"])

    w_overwrite = v.Switch(
        v_model=obj.overwrite, inset=True, label="Overwrite SEPAL images"
    )
    w_overwrite.observe(partial(bind_change, obj=obj, attr="overwrite"), "v_model")

    w_remove = v.Switch(
        v_model=obj.rmdrive, inset=True, label="Remove Google Drive Images"
    )
    w_remove.observe(partial(bind_change, obj=obj, attr="rmdrive"), "v_model")

    out = widgets.Output()
    btn = s.Btn(text="Download", icon="download")

    # Create an alert element for the process
    process_alert = s.Alert()

    on_download(obj, w_selection, btn, out, process_alert)

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
            v.Flex(
                xs12=True,
                children=[
                    v.Sheet(
                        class_="pa-5",
                        children=[
                            widgets.HTML(html_header),
                            w_selection,
                            w_overwrite,
                            w_remove,
                            btn,
                            process_alert,
                            out,
                        ],
                    )
                ],
            )
        ],
    )

    return download_content
