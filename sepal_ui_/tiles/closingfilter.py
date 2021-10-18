#!/usr/bin/env python3

import os
from functools import partial

from traitlets import HasTraits, Unicode, observe
from ipywidgets import Output, HTML
import ipyvuetify as v

from sepal_ui import sepalwidgets as s


def close_filter_tile(w_selector):

    def on_click(widget, event, data, out, obj, alert):

        # Get the current path
        process_path = obj.get_current_path()

        # Clear output if there is something printed before
        out.clear_output()

        # Once the button is clicked, disable it
        btn.disable()

        # Clear old alert messages
        alert.clear()

        @out.capture()
        def run_process(obj):

            run_filter(
                process_path,
                alert,
        )

        run_process(obj)
        btn.activate()

    out = Output()
    btn = s.Btn(text="Start")


    # Create an alert element for the process
    alert = s.Alert()

    content = v.Layout(
        xs12=True,
        row=True,
        class_="ma-5 d-block",
        children=[
            filter_text,
            w_selector, 
            btn,
            alert,
            out,
        ])
    
    btn.on_event('click', partial(
        on_click,
        obj=w_selector,
        out=out,
        alert=alert, 
    ))

    return content