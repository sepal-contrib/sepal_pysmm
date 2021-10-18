#!/usr/bin/env python3


def run_process_tile(aoi, dates):
    """Display the given input values and start de process"""

    # Instantiate an Output() widget to capture the module outputs.
    # such as stderr or stdout

    out = widgets.Output()
    btn = s.Btn(text="Start")

    # Create an alert element for the process
    process_alert = s.Alert()

    content = v.Layout(
        _metadata={"mount_id": "aoi_widget"},
        xs12=True,
        row=True,
        class_="ma-5 d-block",
        children=[
            btn,
            process_alert,
            out,
        ],
    )
    wb.bin_pysmm_process(aoi, dates, btn, out, process_alert)
    return content
