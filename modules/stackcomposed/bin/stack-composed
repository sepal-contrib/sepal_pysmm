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
import os, sys
import argparse
from datetime import datetime
from multiprocessing import cpu_count

# add project dir to pythonpath
project_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if project_dir not in sys.path:
    sys.path.append(project_dir)

from stack_composed import stack_composed, epilog


def script():
    """
    Run as a script with arguments
    """

    # Create parser arguments
    parser = argparse.ArgumentParser(
        prog='stack-composed',
        description='Compute and generate the composed of a raster images stack',
        epilog=epilog,
        formatter_class=argparse.RawTextHelpFormatter)

    def date_validator(s):
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except ValueError:
            msg = "not a valid date: '{0}'".format(s)
            raise argparse.ArgumentTypeError(msg)

    def nodata_validator(s):
        try:
            return float(s)
        except ValueError:
            def split_condition(str_cond):
                str_cond = str_cond.strip().replace(" ", "")
                if str_cond[1] == "=":
                    return [str_cond[0:2], float(str_cond[2::])]
                else:
                    return [str_cond[0:1], float(str_cond[1::])]
            try:
                if "or" in s:
                    conditions = [split_condition(str_cond) for str_cond in s.split("or")]
                    return conditions
                else:
                    return [split_condition(s)]
            except:
                msg = "not a valid condition to define the nodata: '{0}'".format(s)
                raise argparse.ArgumentTypeError(msg)

    parser.add_argument('-stat', type=str, help='Statistic for compute the composed', required=True)
    parser.add_argument('-bands', type=str, help='Band or bands to process, e.g. 1,2,3', required=True)
    parser.add_argument('-nodata', type=nodata_validator, required=False,
                        help='Input pixel value to treat as nodata, e.g: 0, "<0", ">=0", "<0 or >1", ">=0 or <=1"')
    parser.add_argument('-o', type=str, dest='output', help='output directory and/or filename for save results',
                        default=os.getcwd())
    parser.add_argument('-ot', type=str, dest='output_type', help='Output data type for results', required=False,
                        choices=('byte', 'uint16', 'uint32', 'int16', 'int32', 'float32', 'float64'))
    parser.add_argument('-p', type=int, default=cpu_count() - 1,
                        help='Number of process', required=False)
    parser.add_argument('-chunks', type=int, default=1000,
                        help='Chunks size for parallel process', required=False)
    parser.add_argument('-start', type=date_validator, dest='start_date',
                        help='Initial date for filter data, format YYYY-MM-DD', required=False)
    parser.add_argument('-end', type=date_validator, dest='end_date',
                        help='End date for filter data, format YYYY-MM-DD', required=False)
    parser.add_argument('inputs', type=str, help='Directories or images files to process', nargs='*')

    args = parser.parse_args()

    stack_composed.run(args.stat, args.bands, args.nodata, args.output, args.output_type, args.p, args.chunks,
                       args.start_date, args.end_date, args.inputs)

if __name__ == '__main__':
    script()
