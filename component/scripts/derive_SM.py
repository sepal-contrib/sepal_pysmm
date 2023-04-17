#!/usr/bin/env python3

import datetime
import logging
import os
import time
from copy import deepcopy

import ee
import numpy as np
import pandas as pd

from .GEE_wrappers import GEE_extent

logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)


def create_out_name(year, month, day, file_sufix):
    year = str(year)
    month = str(month)
    day = str(day)

    if len(day) < 2:
        day = f"0{day}"
    if len(month) < 2:
        month = f"0{month}"
    return f"SMCmap_{year}_{month}_{day}_{file_sufix}"


def gldas_date():
    ee.Initialize()
    gldas_test = ee.ImageCollection("NASA/GLDAS/V021/NOAH/G025/T3H").select(
        "SoilMoi0_10cm_inst"
    )
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


def get_map(
    minlon,
    minlat,
    maxlon,
    maxlat,
    outpath,
    alert,
    sampling=100,
    year=None,
    month=None,
    day=None,
    tracknr=None,
    overwrite=False,
    tempfilter=True,
    mask="Globcover",
    masksnow=True,
    filename=None,
    start_date=False,
    stop_date=False,
    counter=0,
    **model_kwargs,
):
    """
    Get S1 soil moisture map.

    Atributes:
    minlon, minlat, maxlon, maxlat: (float) extent of soil moisture map
    outpath: (string) destination for soil moisture map export
    sampling: (integer) map sampling
    year, month, day (optional): specify date for extracted map - if not specified, the entire
                                 time-series of maps will be extracted; if specified, the S1 acquisition
                                 closest (in time) will be selected
    tracknr (optional): (integer) Use data from a specific Sentinel-1 track only
    tempfilter: (boolean) apply multi-temporal speckle filter
    mask: (string) select 'Globcover' or 'Corine' (europe only) land-cover classifications for the
           masking of the map
    masksnow: (boolean) apply snow mask
    filename: (string) add to file name

    """
    if "ascending" in model_kwargs:
        ascending = model_kwargs["ascending"]

    if filename is not None:
        if not isinstance(filename, str):
            filename = str(filename)
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    tasks_file_name = os.path.join(outpath, f"task_{now}.txt")

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

    if year is not None:
        asked_date = datetime.datetime(year, month, day).date()
        gldas_last_date = gldas_date()
        if asked_date <= gldas_last_date:
            alert.add_msg(f"Processing the closest image to {year}-{month}-{day}...")

            tasks = []

            time.perf_counter()

            GEE_interface = GEE_extent(
                minlon, minlat, maxlon, maxlat, outpath, sampling=sampling
            )

            # retrieve S1
            GEE_interface.get_S1(
                year,
                month,
                day,
                tempfilter=tempfilter,
                applylcmask=maskcorine,
                mask_globcover=maskglobcover,
                trackflt=tracknr,
                masksnow=masksnow,
                ascending=ascending,
            )

            # retrieve GLDAS
            GEE_interface.get_gldas()
            if GEE_interface.GLDAS_IMG is None:
                return
            # get Globcover
            GEE_interface.get_globcover()
            # get the SRTM
            GEE_interface.get_terrain()

            outname = create_out_name(
                GEE_interface.S1_DATE.year,
                GEE_interface.S1_DATE.month,
                GEE_interface.S1_DATE.day,
                filename,
            )

            # Estimate soil moisture
            GEE_interface.estimate_SM()

            time.perf_counter()
            alert.append_msg(f"Image {outname}.tif processed")

            task, f_name = export_sm(GEE_interface, outname)
            tasks.append(f"{task.id}, {f_name}\n")

            # Write the text file
            with open(tasks_file_name, "a") as tasks_file:
                tasks_file.write(f"{task.id}, {f_name}\n")

            # alert.update_progress(1, total=1)

            return tasks
        else:
            alert.add_msg(
                f"There is not image available for the requested date. \
                Try with a date before to {gldas_last_date}.",
                type_="warning",
            )
    else:
        # if no specific date was specified extract entire time series or a range
        GEE_interface = GEE_extent(
            minlon, minlat, maxlon, maxlat, outpath, sampling=sampling
        )

        # get list of S1 dates
        dates = GEE_interface.get_S1_dates(tracknr=tracknr, ascending=ascending)

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
        tasks = []

        for dateI, _ in dates.iterrows():
            GEE_interface2 = deepcopy(GEE_interface)
            GEE_interface2.get_S1(
                dateI.year,
                dateI.month,
                dateI.day,
                tempfilter=tempfilter,
                applylcmask=maskcorine,
                mask_globcover=maskglobcover,
                trackflt=tracknr,
                masksnow=masksnow,
                ascending=ascending,
            )
            # retrieve GLDAS
            GEE_interface2.get_gldas()
            if GEE_interface2.GLDAS_IMG is not None:
                outname = create_out_name(
                    GEE_interface2.S1_DATE.year,
                    GEE_interface2.S1_DATE.month,
                    GEE_interface2.S1_DATE.day,
                    filename,
                )

                alert.append_msg(f"Processing: {outname}...")

                # get Globcover
                GEE_interface2.get_globcover()

                # get the SRTM
                GEE_interface2.get_terrain()

                # Estimate soil moisture

                GEE_interface2.estimate_SM()

                # Export each image and get the task name and id
                task, f_name = export_sm(GEE_interface2, outname)
                tasks.append(f"{task.id}, {f_name}\n")

                # Write the text file
                with open(tasks_file_name, "a") as tasks_file:
                    tasks_file.write(f"{task.id}, {f_name}\n")
                del GEE_interface2

                # Finish time count

            counter += 1
            # alert.update_progress(counter, total=len(dates))

        GEE_interface = None

        return tasks


def calculate_sm(minlon, minlat, maxlon, maxlat, outpath):
    GEE_interface = GEE_extent(
        minlon, minlat, maxlon, maxlat, outpath, sampling=sampling
    )

    # retrieve S1
    GEE_interface.get_S1(
        year,
        month,
        day,
        tempfilter=tempfilter,
        applylcmask=maskcorine,
        mask_globcover=maskglobcover,
        trackflt=tracknr,
        masksnow=masksnow,
        ascending=ascending,
    )

    # retrieve GLDAS
    GEE_interface.get_gldas()
    if GEE_interface.GLDAS_IMG is None:
        return

    # get Globcover
    GEE_interface.get_globcover()

    # get the SRTM
    GEE_interface.get_terrain()

    outname = create_out_name(
        GEE_interface.S1_DATE.year,
        GEE_interface.S1_DATE.month,
        GEE_interface.S1_DATE.day,
        filename,
    )

    # Estimate soil moisture
    GEE_interface.estimate_SM()

    time.perf_counter()
    alert.append_msg(f"Image {outname}.tif processed")

    task, f_name = export_sm(GEE_interface, outname)
    tasks.append(f"{task.id}, {f_name}\n")

    # Write the text file
    with open(tasks_file_name, "a") as tasks_file:
        tasks_file.write(f"{task.id}, {f_name}\n")
