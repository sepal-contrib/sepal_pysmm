from pathlib import Path
import subprocess
import os
import sys
import ntpath
import re

from time import sleep
from osgeo import gdal
from tqdm.auto import tqdm


def filter_closing(image, tmp_path):

    tmp_image = os.path.join(tmp_path, "tmp_closing.tif")
    process = subprocess.run(
        [
            "otbcli_GrayScaleMorphologicalOperation",
            "-in",
            image,
            "-out",
            tmp_image,
            "-structype",
            "ball",
            "-xradius",
            "1",
            "-yradius",
            "1",
            "-filter",
            "closing",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    return process, tmp_image


def gdal_calculation(image, tmp_image, out_path):

    image_name = ntpath.basename(image)
    closed_image = os.path.join(out_path, "close_" + image_name)

    process = subprocess.run(
        [
            "gdal_calc.py",
            "-A",
            image,
            "-B",
            tmp_image,
            "--NoDataValue=0",
            "--co=COMPRESS=LZW",
            "--type=UInt16",
            "--overwrite",
            "--outfile=" + closed_image,
            "--calc=B*(A==0)+A",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    return process


def remove_tmp_image(tmp_image):
    os.remove(tmp_image)
    return


def get_dimension(image):
    raster = gdal.Open(image)
    return [raster.RasterXSize, raster.RasterYSize]


def raw_to_processed(image, alert):

    image_name = Path(image).name
    out_close_path = str(Path(image).parent).replace("0_raw", "1_processed")
    Path(out_close_path).mkdir(parents=True, exist_ok=True)
    out_image = Path(out_close_path, f"close_{image_name}")

    if not out_image.exists():

        message = f"Processing: {image_name}..."
        alert.append_msg(message)
        filter_process, tmp_image = filter_closing(image, str(out_close_path))
        if filter_process.returncode == 0:
            gdal_process = gdal_calculation(image, tmp_image, str(out_close_path))
            if gdal_process.returncode == 0:
                remove_tmp_image(tmp_image)
            else:
                raise Exception(gdal_process.stderr)
        else:
            raise Exception(filter_process.stderr)
    else:
        message = f'Skipping: Image "{image_name}" already exists'
        alert.append_msg(message)

    # this process is fast, so, let's wat some time after ach iteration
    sleep(0.5)


def run_filter(process_path, recursive, alert, output):

    if not process_path:
        raise Exception("Please select a folder containing .tif images.")

    image_files = [
        str(image)
        for folder in process_path
        for image in (
            list(Path(folder).glob("[!.]*.tif"))
            if not recursive
            else list(Path(folder).rglob("[!.]*.tif"))
        )
    ]

    if not image_files:
        raise Exception(
            f"Error: The given folders doesn't have any .tif image to process, "
            "please make sure you have processed and downloaded the images, in the "
            "step 1 and 2. Or try with a different folder."
        )
    else:
        dimension = get_dimension(image_files[0])
        alert.add_msg(
            f"There are {len(image_files)} images to process, please wait...",
            type_="info",
        )
        alert.append_msg(f"The image dimension is {dimension[0]} x {dimension[1]} px")

    with output:
        output.clear_output()
        global pbar
        pbar = tqdm(
            total=len(image_files),
            dynamic_ncols=True,
            bar_format="{l_bar}{bar}{n_fmt}/{total_fmt}",
        )

    for image in image_files:
        raw_to_processed(image, alert)
        pbar.update(1)

    pbar.close()
