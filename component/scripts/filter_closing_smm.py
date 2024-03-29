import ntpath
import os
import subprocess
from pathlib import Path
from time import sleep

from osgeo import gdal


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
        alert.append_msg(f"Processing: {image_name}...")
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
        alert.append_msg(f'Skipping: Image "{image_name}" already exists')

    # this process is fast, so, let's wat some time after ach iteration
    sleep(0.5)
