#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Stack Composed
#
#  Copyright (C) 2016-2018 Xavier Corredor Llano, SMBYC
#  Email: xcorredorl at ideam.gov.co
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import os
import re
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'stack_composed', '__init__.py'), encoding='utf-8') as fp:
    version = re.search("__version__ = '([^']+)'", fp.read()).group(1)
try:
    import pypandoc
    # convert md to rst for PyPi
    long_description = pypandoc.convert(os.path.join(here, 'README.md'), 'rst')
except(IOError, ImportError):
    with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
        long_description = f.read()

setup(
    name='stack-composed',
    version=version,
    description='Compute and generate the composed of a raster images stack',
    long_description=long_description,
    author='Xavier Corredor Llano, SMBYC',
    author_email='xcorredorl@ideam.gov.co',
    url='https://smbyc.bitbucket.io/stackcomposed',
    license='GPLv3',
    packages=find_packages(),
    install_requires=['gdal',
                      'numpy',
                      'dask[array]',
                      'dask[bag]',
                      'cloudpickle'],
    scripts=['bin/stack-composed'],
    platforms=['Any'],
    keywords='stack composed statistics landsat raster gis',
    classifiers=[
        "Topic :: Scientific/Engineering :: GIS",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python",
        "Environment :: Console",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)"],
)
