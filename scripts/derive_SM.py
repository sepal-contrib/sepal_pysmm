import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import time

from GEE_wrappers import GEE_extent
from GEE_wrappers import GEE_pt


def get_map(minlon, minlat, maxlon, maxlat,
            outpath,
            sampling=100,
            year=None, month=None, day=None,
            tracknr=None,
            overwrite=False,
            tempfilter=True,
            mask='Globcover',
            masksnow=True,
            filename=None):
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
        if isinstance(filename, str):
            print(filename)
        else:
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

        outname = 'SMCmap_' + \
                  str(GEE_interface.S1_DATE.year) + '_' + \
                  str(GEE_interface.S1_DATE.month) + '_' + \
                  str(GEE_interface.S1_DATE.day) + '_' + \
                  filename

        # Estimate soil moisture
        GEE_interface.estimate_SM()

        #GEE_interface.GEE_2_disk(name=outname, timeout=False)

        #GEE_interface = None


        finish = time.perf_counter()
        print('Finished the image {} in {} seconds, and using the {} processor'.format(outname, round(finish-start,2), os.getpid()))

        return GEE_interface


    else:

        # if no specific date was specified extract entire time series
        GEE_interface = GEE_extent(minlon, minlat, maxlon, maxlat, outpath, sampling=sampling)

        # get list of S1 dates
        dates = GEE_interface.get_S1_dates(tracknr=tracknr)
        dates = np.unique(dates)

        for dateI in dates:
            # retrieve S1
            GEE_interface.get_S1(dateI.year, dateI.month, dateI.day,
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

            outname = 'SMCmap_' + \
                      str(GEE_interface.S1_DATE.year) + '_' + \
                      str(GEE_interface.S1_DATE.month) + '_' + \
                      str(GEE_interface.S1_DATE.day) + '_' + \
                      filename

            if overwrite == False and os.path.exists(outpath + outname + '.tif'):
                print(outname + ' already done')
                continue

            # Estimate soil moisture
            GEE_interface.estimate_SM()

            GEE_interface.GEE_2_disk(name=outname, timeout=False)

        GEE_interface = None

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
