import datetime as dt
import logging
from pathlib import Path

import component.parameter as param
import component.scripts.scripts as cs
from component.scripts.derive_SM import get_map

logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)


def run_pysmm(aoi_model, date_model, model, alert, counter):
    """
    Process the input variables to start the "derive_sm" module.

    Args:
    ----
        Aoi (AoiModel): Aoi Model which stores the inputs from the user
        Date (DateSelector): Date selector custom widget which stores the input data from the user
    """
    # Get SEPAL user
    user = Path("~").expanduser().parts[-1]

    single_date = False

    if not aoi_model.feature_collection:
        raise Exception("Please select an Area of Interest in step 2: 'AOI selection'.")

    if not date_model.date_method:
        raise Exception("Please select the analysis dates in step 3: 'Date Selection'.")

    if date_model.date_method == "single":
        if not date_model.single_date:
            raise Exception(
                f"You have selected the {date_model.date_method} method but not selected a date."
            )
        date = dt.datetime.strptime(date_model.single_date, "%Y-%m-%d")
        single_date = True
        year, month, day = date.year, date.month, date.day

    elif date_model.date_method == "range":
        if not all([date_model.start_date, date_model.end_date]):
            raise Exception(
                f"You have selected the {date_model.date_method} method but not selected a date."
            )
        start_date = dt.datetime.strptime(date_model.start_date, "%Y-%m-%d").date()
        stop_date = dt.datetime.strptime(date_model.end_date, "%Y-%m-%d").date()
    else:
        # The selected attribute is all time series
        year, month, day = False, False, False
        start_date = False

    # Read EE coordinates
    minlon, minlat, maxlon, maxlat = cs.get_bounds(aoi_model.feature_collection)

    # Create a subfolder when is a filter selection
    if aoi_model.method in ["SHAPE", "ASSET"]:
        
        if aoi_model.asset_json["pathname"] or aoi_model.vector_json["pathname"]:
            # Create a folder to download pysmm images

            json = (
                aoi_model.asset_json
                if aoi_model.method == "ASSET"
                else aoi_model.vector_json
            )

            name = str(Path(json["pathname"]).name)
            column = str(json["column"])
            value = str(json["value"]) if json["value"] else ""

            outpath = Path(param.RAW_DIR, name, column, value)

            file_sufix = f"{user}_{name}_{column}_{value}"
    else:
        # For all the other types of selections
        outpath = Path(param.RAW_DIR, aoi_model.name)
        file_sufix = f"{aoi_model.name}"

    outpath.mkdir(exist_ok=True, parents=True)

    args = (minlon, minlat, maxlon, maxlat, str(outpath))
    kwargs = {
        "alert": alert,
        "sampling": 100,
        "tracknr": None,
        "tempfilter": True,
        "mask": "Globcover",
        "masksnow": False,
        "overwrite": True,
        "filename": file_sufix,
        "year": None,
        "month": None,
        "day": None,
        "start_date": False,
        "stop_date": False,
        "ascending": model.ascending,
        "counter": counter,
    }

    # To process single date or non row dates.

    if single_date:
        kwargs["year"] = year
        kwargs["month"] = month
        kwargs["day"] = day
        tasks = get_map(*args, **kwargs)
    # To get the the series map in row
    else:
        # To get the series map in a specified range
        if start_date:
            kwargs["start_date"] = start_date
            kwargs["stop_date"] = stop_date
            tasks = get_map(*args, **kwargs)
        # To retreive the entire series
        else:
            tasks = get_map(*args, **kwargs)
    if tasks:
        alert.append_msg(
            (
                "Done: The images are being processed into your GEE account."
                "Now you can close your SEPAL session and use the download tool "
                "when the process is done."
            ),
            section=True,
            type_="success",
        )
    del tasks
