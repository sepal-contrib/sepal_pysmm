import concurrent.futures
import datetime
import logging
import os
from typing import Tuple

import ee
import numpy as np
import pandas as pd
import component.scripts.scripts as cs

from .GEE_wrappers import GEE_extent

logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)

ee.Initialize()


def get_map(
    aoi,
    outpath,
    alert,
    images_span,
    chips_span,
    year=None,
    month=None,
    day=None,
    overwrite=False,
    tempfilter=False,
    mask="Globcover",
    masksnow=True,
    file_suffix=None,
    start_date=False,
    stop_date=False,
    grid_size=0.5,
    chip_process=False,
    **model_kwargs,
):
    """
    Get S1 soil moisture map.

    Atributes:
        aoi: (ee.FeatureCollection) area of interest
        outpath: (string) destination for soil moisture map export
        alert: sw.Alert object to send messages to the user
        year, month, day (optional): specify date for extracted map
             - if not    specified, the entire time-series of maps will be extracted;
             - if specified, the S1 acquisition closest (in time) will be selected
        tempfilter: (boolean) apply multi-temporal speckle filter
        mask: (string) select 'Globcover' or 'Corine' (europe only) land-cover classifications for the
            masking of the map
        masksnow: (boolean) apply snow mask
        filename: (string) add to file name

    """
    if "ascending" in model_kwargs:
        ascending = model_kwargs["ascending"]

    if file_suffix is not None:
        if not isinstance(file_suffix, str):
            file_suffix = str(file_suffix)

    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    tasks_file_name = os.path.join(outpath, f"task_{now}.txt")

    # Make sure the file is empty before starting
    with open(tasks_file_name, "w") as file:
        pass

    maskcorine = False
    maskglobcover = False

    if mask == "Globcover":
        maskglobcover = True
    elif mask == "Corine":
        maskcorine = True
    else:
        raise Exception(
            f"{mask} is not recognised as a valid land-cover classification"
        )

    # Chop into small pieces from 0.5 degrees
    # We need to create a process for each of the tiles that we are going to create
    chip_bounds = cs.get_geogrid_bounds(
        aoi.geometry(), cell_size_deg=grid_size, chip_process=chip_process
    )

    if year is not None:
        asked_date = datetime.datetime(year, month, day).date()
        gldas_last_date = gldas_date()
        if asked_date <= gldas_last_date:
            alert.add_msg(f"Processing the closest image to {year}-{month}-{day}...")

            alert.children = alert.children + [
                images_span,
                ", ",  # empty space
                chips_span,
            ]

            images_span.set_total(1)
            chips_span.set_total(len(chip_bounds))

            tasks = []

            tasks += get_sm(
                chip_bounds=chip_bounds,
                year=year,
                month=month,
                day=day,
                tempfilter=tempfilter,
                maskcorine=maskcorine,
                maskglobcover=maskglobcover,
                masksnow=masksnow,
                ascending=ascending,
                suffix=file_suffix,
                tasks_file_name=tasks_file_name,
                images_span=images_span,
                chips_span=chips_span,
            )

            return tasks
        else:
            alert.add_msg(
                f"There is not image available for the requested date. \
                Try with a date before to {gldas_last_date}.",
                type_="warning",
            )
    else:
        # if no specific date was specified extract entire time series or a range

        dates = get_dates(aoi, ascending, start_date, stop_date, alert)

        alert.children = alert.children + [
            images_span,
            " ",  # empty space
            chips_span,
        ]

        images_span.set_total(len(dates))
        chips_span.set_total(len(chip_bounds) * len(dates))

        tasks = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            futures = [
                executor.submit(
                    get_sm,
                    chip_bounds=chip_bounds,
                    year=dateI.year,
                    month=dateI.month,
                    day=dateI.day,
                    tempfilter=tempfilter,
                    maskcorine=maskcorine,
                    maskglobcover=maskglobcover,
                    masksnow=masksnow,
                    ascending=ascending,
                    suffix=file_suffix,
                    tasks_file_name=tasks_file_name,
                    images_span=images_span,
                    chips_span=chips_span,
                )
                for dateI, _ in dates.iterrows()
            ]

            for future in concurrent.futures.as_completed(futures):
                tasks += future.result()

        return tasks


def create_out_name(year, month, day, orbit, file_suffix):
    year = str(year)
    month = str(month)
    day = str(day)

    orbit_prefix = orbit[:4]

    if len(day) < 2:
        day = f"0{day}"
    if len(month) < 2:
        month = f"0{month}"

    return f"SMCmap_{year}_{month}_{day}_{orbit_prefix}_{file_suffix}"


def gldas_date():
    gldas_test = ee.ImageCollection("NASA/GLDAS/V021/NOAH/G025/T3H").select(
        "SoilMoi0_10cm_inst"
    )
    # Get the last date of the GLDAS dataset
    last_gldas = gldas_test.aggregate_max("system:index").getInfo()
    last_date = datetime.datetime(
        int(last_gldas[1:5]), int(last_gldas[5:7]), int(last_gldas[7:9])
    ).date()
    return last_date


def export_sm(image, file_name):
    description = f"fileexp_{file_name}"

    task = ee.batch.Export.image.toDrive(
        image=image.__getattribute__("ESTIMATED_SM"),
        description=description,
        fileNamePrefix=file_name,
        scale=100,
        region=image.roi.getInfo()["coordinates"],
        maxPixels=1e13,
    )
    task.start()
    return task, file_name


def get_dates(aoi, ascending, start_date, stop_date, alert):
    """
    Get dates of available S1 images.

    Atributes:
    minlon, minlat, maxlon, maxlat: (float) extent of soil moisture map
    ascending: (boolean) select ascending or descending orbit
    start_date, stop_date: (string) select a range of dates

    """
    minlon, minlat, maxlon, maxlat = cs.get_bounds(aoi)

    # get GEE interface
    GEE_interface = GEE_extent(minlon, minlat, maxlon, maxlat)

    # get list of S1 dates
    dates = GEE_interface.get_S1_dates(ascending=ascending)

    # get unique dates
    dates = pd.DataFrame(np.unique(dates)).set_index(0).sort_index()
    gldas_last_date = gldas_date()
    if not gldas_last_date:
        raise Exception("There is not.")

    if start_date:
        # The user has selected a range
        dates = dates[start_date:stop_date]
        dates = dates[:gldas_last_date]
        if len(dates) == 0:
            raise Exception("No images available for the selected range.")

        first = dates.index.to_list()[0]
        last = dates.tail(1).index.to_list()[0]

        alert.append_msg(
            f"Processing all images available between {start_date} and {stop_date}..."
        )
        alert.append_msg(f"There are {len(dates)} unique images.")
        alert.append_msg(
            f"The first available date is {first} and the last is {last}.\n"
        )
    else:
        # The user has selected the entire series
        first = dates.index.to_list()[0]
        dates = dates[:gldas_last_date]

        last = dates.tail(1).index.to_list()[0]

        alert.append_msg("Processing all available images in the time series...")
        # alert.update_progress(0, total=len(dates))
        alert.append_msg(f"There are {len(dates)} unique images.\n")
        alert.append_msg(
            f"The first available date is {first} and the last is {last}.\n"
        )

    return dates


def get_sm(
    chip_bounds,
    year,
    month,
    day,
    tempfilter,
    maskcorine,
    maskglobcover,
    masksnow,
    ascending,
    suffix,
    tasks_file_name,
    images_span,
    chips_span,
):
    """Instantiate the GEE interface and run the S1 and GLDAS retrievals to get the SM map."""

    def sm_process(
        i: int, chip_bound: Tuple[float, float, float, float], n_chips: int
    ) -> str:
        minlon, minlat, maxlon, maxlat = chip_bound

        # get GEE interface
        GEE_interface = GEE_extent(minlon, minlat, maxlon, maxlat)

        # retrieve S1
        GEE_interface.get_S1(
            year,
            month,
            day,
            tempfilter=tempfilter,
            applylcmask=maskcorine,
            mask_globcover=maskglobcover,
            masksnow=masksnow,
            ascending=ascending,
        )

        # retrieve GLDAS
        GEE_interface.get_gldas()

        if GEE_interface.GLDAS_IMG is not None:
            outname = create_out_name(
                GEE_interface.S1_DATE.year,
                GEE_interface.S1_DATE.month,
                GEE_interface.S1_DATE.day,
                GEE_interface.ORBIT,
                suffix + f"chip_{i}",
            )

            if n_chips == 1:
                outname = outname.replace("chip_0", "")

            # get Globcover
            GEE_interface.get_globcover()

            # get the SRTM
            GEE_interface.get_terrain()

            # Estimate soil moisture
            GEE_interface.estimate_SM()

            # Export each image and get the task name and id
            task, f_name = export_sm(GEE_interface, outname)

            task_line = f"{task.id}, {f_name}\n"

            # Write the text file
            with open(tasks_file_name, "a") as tasks_file:
                tasks_file.write(task_line)

            chips_span.update()

            return task_line

    tasks = []
    n_chips = len(chip_bounds)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        futures = [
            executor.submit(sm_process, i=i, chip_bound=chip_bound, n_chips=n_chips)
            for i, chip_bound in enumerate(chip_bounds)
        ]

        for future in concurrent.futures.as_completed(futures):
            tasks += future.result()

        images_span.update()

    return tasks
