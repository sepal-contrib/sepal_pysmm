#!/usr/bin/env python3

import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import time
import ee
import datetime
from tqdm import tqdm
from copy import deepcopy


from .GEE_wrappers import GEE_extent
from .GEE_wrappers import GEE_pt

def create_out_name(year, month, day, file_sufix):
    
    year = str(year)
    month = str(month)
    day = str(day)

    if len(day) < 2:
        day = f'0{day}'
    if len(month) < 2:
        month = f'0{month}'

    return f'SMCmap_{year}_{month}_{day}_{file_sufix}'

def gldas_date():
    ee.Initialize()
    gldas_test = ee.ImageCollection("NASA/GLDAS/V021/NOAH/G025/T3H") \
        .select('SoilMoi0_10cm_inst')
    last_gldas = gldas_test.aggregate_max('system:index').getInfo()
    last_date = datetime.datetime(int(last_gldas[1:5]), int(last_gldas[5:7]), int(last_gldas[7:9])).date()
    return last_date

def export_sm(image, file_name):
    
    description = f'fileexp_{file_name}'
    
    task = ee.batch.Export.image.toDrive(
        image=image.__getattribute__('ESTIMATED_SM'),
        description=description,
        fileNamePrefix=file_name,
        scale=image.sampling,
        region=image.roi.getInfo()['coordinates'],
        maxPixels=1000000000000
    )
    task.start()
    return task, file_name

def get_map(minlon, minlat, maxlon, maxlat,
            outpath,
            sampling=100,
            year=None, month=None, day=None,
            tracknr=None,
            overwrite=False,
            tempfilter=True,
            mask='Globcover',
            masksnow=True,
            filename=None, 
            start_date=False,
            stop_date=False
            ):

    """Get S1 soil moisture map

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
    if filename is not None:
        if not isinstance(filename, str):
            filename = str(filename)
        
    maskcorine = False
    maskglobcover = False

    if mask == 'Globcover':
        maskglobcover = True
    elif mask == 'Corine':
        maskcorine = True
    else:
        print(mask + ' is not recognised as a valid land-cover classification')
        return

    if year is not None:
        asked_date = datetime.datetime(year, month, day).date()
        gldas_last_date = gldas_date()
        if asked_date <= gldas_last_date:
            print(f'Processing the closest image to {year}-{month}-{day}...')
            maps = []

            start = time.perf_counter()

            GEE_interface = GEE_extent(minlon, minlat, maxlon, maxlat, outpath, sampling=sampling)

            # retrieve S1
            GEE_interface.get_S1(year, month, day,
                                 tempfilter=tempfilter,
                                 applylcmask=maskcorine,
                                 mask_globcover=maskglobcover,
                                 trackflt=tracknr,
                                 masksnow=masksnow)

            # retrieve GLDAS
            GEE_interface.get_gldas()
            if GEE_interface.GLDAS_IMG is None:
                return
            # get Globcover
            GEE_interface.get_globcover()
            # get the SRTM
            GEE_interface.get_terrain()

            outname = create_out_name(GEE_interface.S1_DATE.year, 
                                        GEE_interface.S1_DATE.month,
                                        GEE_interface.S1_DATE.day, 
                                        filename)

            # Estimate soil moisture
            GEE_interface.estimate_SM()


            finish = time.perf_counter()
            print('The image {} has been processed in {} seconds'.format(outname, round(finish-start,2)))

            maps.append([GEE_interface, outname])
            return maps
        else:
            print('There is no image available for the requested date.')
            print(f'Try with a date before to {gldas_last_date}.')

    else:
        
        # if no specific date was specified extract entire time series
        GEE_interface = GEE_extent(minlon, minlat, maxlon, maxlat, outpath, sampling=sampling)

        #get list of S1 dates
        dates = GEE_interface.get_S1_dates(tracknr=tracknr)
        
        dates = pd.DataFrame(np.unique(dates)).set_index(0).sort_index()
        gldas_last_date = gldas_date()
        if start_date:
            # The user has selected a range
            dates = dates[start_date:stop_date]
            dates = dates[:gldas_last_date]

            first=dates.index.to_list()[0]
            last=dates.tail(1).index.to_list()[0]
            
            print(f'Processing all images available between {start_date} and {stop_date}...')
            print(f'There are {len(dates)} unique images.')
            print(f'The first available date is {first} and the last is {last}.\n')

        else:
            # The user has selected the entire series
            first = dates.index.to_list()[0]
            dates = dates[:gldas_last_date]

            last = dates.tail(1).index.to_list()[0]
            print(f'Processing all available images in the time series...')
            print(f'There are {len(dates)} unique images.\n')
            print(f'The first available date is {first} and the last is {last}.\n')

        tasks = []
        i = 0

        pbar = tqdm(total = len(dates))
        for dateI, rows in dates.iterrows():
            start = time.perf_counter()
            GEE_interface2 = deepcopy(GEE_interface)

            GEE_interface2.get_S1(dateI.year, dateI.month, dateI.day,
                               tempfilter=tempfilter,
                               applylcmask=maskcorine,
                               mask_globcover=maskglobcover,
                               trackflt=tracknr,
                               masksnow=masksnow)
            # retrieve GLDAS
            GEE_interface2.get_gldas()
            if GEE_interface2.GLDAS_IMG is not None:
                
                outname = create_out_name(GEE_interface2.S1_DATE.year, 
                                            GEE_interface2.S1_DATE.month,
                                            GEE_interface2.S1_DATE.day, 
                                            filename)

                pbar.desc = f'Processing: {outname}...'

                # get Globcover
                GEE_interface2.get_globcover()
                
                # get the SRTM
                GEE_interface2.get_terrain()



                # Estimate soil moisture

                GEE_interface2.estimate_SM()

                task, f_name = export_sm(GEE_interface2, outname)
                tasks.append(f"{task.id}, {f_name}\n")

                del GEE_interface2

                # Finish time count
                finish = time.perf_counter()
                

            pbar.update(1)
           #  i += 1
           # if i == 2:
           #    break

        pbar.close()
        GEE_interface = None
        return tasks
        

def get_ts(loc,
           workpath,
           tracknr=None,
           footprint=50,
           masksnow=True,
           calc_anomalies=False,
           create_plots=False,
           names=None):
    """Get S1 soil moisture time-series

        Atributes:
        loc: (tuple or list of tuples) longitude and latitude in decimal degrees
        workpath: destination for output files
        tracknr (optional): Use data from a specific Sentinel-1 track only
        footprint: time-series footprint
        masksnow: apply automatic wet snow mask
        calc_anomalies: (boolean) calculate anomalies
        create_plots: (boolean) generate and save time-series plots to workpath
        names: (string or list of strings, optional): list of time-series names

    """

    if isinstance(loc, list):
        print('list')
    else:
        loc = [loc]

    if names is not None:
        if isinstance(names, list):
            print('Name list specified')
        else:
            names = [names]

    sm_ts_out = list()
    names_out = list()

    cntr = 0
    for iloc in loc:
        # iterate through the list of points to extract
        lon = iloc[0]
        lat = iloc[1]

        if names is not None:
            iname = names[cntr]
        else:
            iname = None

        print('Estimating surface soil moisture for lon: ' + str(lon) + ' lat: ' + str(lat))

        # initialize GEE point object
        gee_pt_obj = GEE_pt(lon, lat, workpath, buffer=footprint)
        sm_ts = gee_pt_obj.extr_SM(tracknr=tracknr, masksnow=masksnow, calc_anomalies=calc_anomalies)

        if isinstance(sm_ts, pd.Series) or isinstance(sm_ts, pd.DataFrame):
            # create plots
            if create_plots == True:
                if calc_anomalies == False:
                    # plot s1 soil moisture vs gldas_downscaled
                    fig, ax = plt.subplots(figsize=(6.5, 2.7))
                    line1, = ax.plot(sm_ts.index, sm_ts,
                                     color='b',
                                     linestyle='-',
                                     marker='+',
                                     label='S1 Soil Moisture',
                                     linewidth=0.2)
                    ax.set_ylabel('Soil Moisture [%-Vol.]')
                    if iname is None:
                        plotname = 's1_sm_' + str(lon) + '_' + str(lat) + '.png'
                    else:
                        plotname = 's1_sm_' + iname + '.png'
                else:
                    fig, ax = plt.subplots(figsize=(6.5, 2.7))
                    line1, = ax.plot(sm_ts.index, sm_ts['ANOM'].values,
                                     color='r',
                                     linestyle='-',
                                     marker='+',
                                     label='S1 Soil Moisture Anomaly',
                                     linewidth=0.2)
                    x0 = [sm_ts.index[0], sm_ts.index[-1]]
                    y0 = [0, 0]
                    line2, = ax.plot(x0, y0,
                                     color='k',
                                     linestyle='--',
                                     linewidth=0.2)
                    ax.set_ylabel('Soil Moisture Anomaly [%-Vol.]')
                    # plt.legend(handles=[line1, line2])
                    if iname is None:
                        plotname = 's1_sm_anom_' + str(lon) + '_' + str(lat) + '.png'
                    else:
                        plotname = 's1_sm_anom_' + iname + '.png'
                plt.setp(ax.get_xticklabels(), fontsize=6)
                plt.savefig(workpath + plotname, dpi=300)
            sm_ts_out.append(sm_ts)
            names_out.append(iname)

        gee_pt_obj = None
        cntr = cntr + 1
    if names is not None:
        return (sm_ts_out, names_out)
    else:
        return sm_ts_out
