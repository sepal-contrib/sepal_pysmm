#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2016-2018 Xavier Corredor Llano, SMBYC
#  Email: xcorredorl at ideam.gov.co
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
import datetime
import os
import re


def calc_date(year, jday):
    return (datetime.datetime(year, 1, 1) + datetime.timedelta(jday - 1)).date()


#### LANDSAT PARSE FILENAME ####


def parse_landsat_ID_oldFilename(file_path):
    """
    Parse the original structure of old Landsat filename

    Examples:
        LC80070592016320LGN00_band1.tif
    """
    filename = os.path.basename(file_path).split("_")[0].split(".")[0]
    filename = filename.upper()
    if filename[1] == "E":
        sensor = "ETM"
    if filename[1] in ["O", "C"]:
        sensor = "OLI"
    if filename[1] == "T":
        sensor = "TM"
    landsat_version = int(filename[2])
    path = int(filename[3:6])
    row = int(filename[6:9])
    year = int(filename[9:13])
    jday = int(filename[13:16])
    date = calc_date(year, jday)
    return landsat_version, sensor, path, row, date, jday


def parse_landsat_ID_newFilename(file_path):
    """
    Parse the original structure of new Landsat filename

    Examples:
        LC08_L1TP_007059_20161115_20170318_01_T2_b1.tif
    """
    filename = os.path.basename(file_path).split("_")[0:4]
    filename = [i.upper() for i in filename]
    if filename[0][1] == "E":
        sensor = "ETM"
    if filename[0][1] in ["O", "C"]:
        sensor = "OLI"
    if filename[0][1] == "T":
        sensor = "TM"
    landsat_version = int(filename[0][-1])
    path = int(filename[2][0:3])
    row = int(filename[2][3:6])
    year = int(filename[3][0:4])
    month = int(filename[3][4:6])
    day = int(filename[3][6:8])
    date = datetime.date(year, month, day)
    jday = date.timetuple().tm_yday
    return landsat_version, sensor, path, row, date, jday


#### SMBYC structure of Landsat filename


def parse_SMBYC_filename(file_path):
    """
    Parse the SMBYC structure of Landsat filename

    Examples:
        Landsat_8_53_020601_7ETM_Reflec_SR_Enmask.tif
    """
    filename = os.path.basename(file_path).split(".")[0]
    path = int(filename.split("_")[1])
    row = int(filename.split("_")[2])
    date = datetime.datetime.strptime(filename.split("_")[3], "%y%m%d").date()
    jday = date.timetuple().tm_yday
    landsat_version = int(filename.split("_")[4][0])
    sensor = filename.split("_")[4][1::]
    return landsat_version, sensor, path, row, date, jday

def parse_other_files(file_path):
    """
    Parse the date structure of other files

    Examples:
        close_SMCmap_2019_11_09_dguerrero_1111.tif
    """
    filename = os.path.basename(file_path).split(".")[0]

    match = re.search(r'\d{4}_\d{2}_\d{2}', filename) 
    date = datetime.datetime.strptime(match.group(), '%Y_%m_%d').date()
    jday = date.timetuple().tm_yday

    path = None
    row = None
    landsat_version = None
    sensor = None
    return landsat_version, sensor, path, row, date, jday


def parse_filename(file_path):
    """
    Extract metadata from filename
    """
    root, filename = os.path.split(file_path)

    try:
        if filename.startswith("Landsat"):
            # SMBYC format
            return parse_SMBYC_filename(file_path)
        elif filename[4] == "_":
            # new ESPA filename
            return parse_landsat_ID_newFilename(file_path)
        else:
            # old filename
            try:
                return parse_landsat_ID_oldFilename(file_path)
            except:
                return parse_other_files(file_path)

    except Exception as err:
        raise Exception("Cannot parse filename for: {}\n\n{}".format(file_path, err))

