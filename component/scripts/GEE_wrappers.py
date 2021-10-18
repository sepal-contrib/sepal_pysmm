#!/usr/bin/env python3

import datetime as dt
import timeit
import math
import os
import pickle
import time
import ee
import numpy as np
import pandas as pd
import pytesmo.time_series.anomaly as anomaly
import warnings

from pytesmo.temporal_matching import df_match
from sklearn.linear_model import LinearRegression
from .utils import gdrive


from sklearn.model_selection import RepeatedKFold, GridSearchCV
import sklearn
from sklearn.svm import SVR
from numpy import array
from sklearn.preprocessing import RobustScaler

import logging
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)


class GEE_pt(object):
    """Class to create an interface with GEE for the extraction of parameter time series

        Attributes:
            lon: longitude in decimal degrees
            lat: latitude in decimal degrees
            workdir: path to a directory to save output e.g. time-series plots
            buffer: radius of the time-series footprint
        """

    def __init__(self, lon, lat, workdir, buffer=20):
        ee.Reset()
        ee.Initialize()
        self.lon = lon
        self.lat = lat
        self.buffer = buffer
        self.workdir = workdir

        # Placeholders
        self.S1TS = None
        self.ASPE = None
        self.SLOP = None
        self.ELEV = None
        self.LC = None

    def _multitemporalDespeckle(self, images, radius, units, opt_timeWindow=None):
        def mapMeanSpace(i):
            reducer = ee.Reducer.mean()
            kernel = ee.Kernel.square(radius, units)
            mean = i.reduceNeighborhood(reducer, kernel).rename(bandNamesMean)
            ratio = i.divide(mean).rename(bandNamesRatio)
            return (i.addBands(mean).addBands(ratio))

        if opt_timeWindow == None:
            timeWindow = dict(before=-3, after=3, units='month')
        else:
            timeWindow = opt_timeWindow

        bandNames = ee.Image(images.first()).bandNames()
        bandNamesMean = bandNames.map(lambda b: ee.String(b).cat('_mean'))
        bandNamesRatio = bandNames.map(lambda b: ee.String(b).cat('_ratio'))

        # compute spatial average for all images
        meanSpace = images.map(mapMeanSpace)

        # computes a multi-temporal despeckle function for a single image

        def multitemporalDespeckleSingle(image):
            t = image.date()
            fro = t.advance(ee.Number(timeWindow['before']), timeWindow['units'])
            to = t.advance(ee.Number(timeWindow['after']), timeWindow['units'])

            meanSpace2 = ee.ImageCollection(meanSpace).select(bandNamesRatio).filterDate(fro, to) \
                .filter(ee.Filter.eq('relativeOrbitNumber_start', image.get('relativeOrbitNumber_start')))

            b = image.select(bandNamesMean)

            return (b.multiply(meanSpace2.sum()).divide(meanSpace2.count()).rename(bandNames)).set('system:time_start',
                                                                                                   image.get(
                                                                                                       'system:time_start'))

        return meanSpace.map(multitemporalDespeckleSingle)

    def _s1_track_ts(self,
                     filtered_collection,
                     track_nr,
                     dual_pol,
                     varmask,
                     returnLIA,
                     masksnow,
                     tempfilter):

        def getLIA(imCollection):
            # function to calculate the local incidence angle, based on azimuth angle and srtm
            srtm = ee.Image("USGS/SRTMGL1_003")
            srtm_slope = ee.Terrain.slope(srtm)
            srtm_aspect = ee.Terrain.aspect(srtm)

            tmpImg = ee.Image(imCollection.first())

            inc = ee.Image(tmpImg).select('angle')

            s = srtm_slope.multiply(ee.Image.constant(277).subtract(srtm_aspect).multiply(math.pi / 180).cos())
            lia = inc.subtract(ee.Image.constant(90).subtract(ee.Image.constant(90).subtract(s))).abs()

            return ee.Image(lia.select(['angle'], ['lia']).reproject(srtm.projection()))

        def miscMask(image):
            # masking of low and high db values as well as areas affected by geometry distortion
            tmp = ee.Image(image)

            # mask pixels
            vv = tmp.select('VV')
            if dual_pol == True:
                vh = tmp.select('VH')
                maskvh = vh.gte(-25).bitwiseAnd(vh.lt(0))  # was -25 and 0
            lia = tmp.select('lia')
            maskvv = vv.gte(-25).bitwiseAnd(vv.lt(0))
            masklia1 = lia.gt(20)  # angle 10
            masklia2 = lia.lt(45)  # angle 50
            masklia = masklia1.bitwiseAnd(masklia2)

            if dual_pol == True:
                mask = maskvv.bitwiseAnd(maskvh)
            else:
                mask = maskvv
            mask = mask.bitwiseAnd(masklia)
            # mask = mask.bitwiseAnd(maskslope)
            tmp = tmp.updateMask(mask)

            return (tmp)

        def toln(image):
            tmp = ee.Image(image)

            # Convert to linear
            vv = ee.Image(10).pow(tmp.select('VV').divide(10))
            if dual_pol == True:
                vh = ee.Image(10).pow(tmp.select('VH').divide(10))

            # Convert to ln
            out = vv.log()
            if dual_pol == True:
                out = out.addBands(vh.log())
                out = out.select(['constant', 'constant_1'], ['VV', 'VH'])
            else:
                out = out.select(['constant'], ['VV'])

            return out.set('system:time_start', tmp.get('system:time_start'))

        def applyvarmask(image):
            tmp = ee.Image(image)
            tmp = tmp.updateMask(varmask)

            return (tmp)

        def tolin(image):
            tmp = ee.Image(image)

            # Convert to linear
            vh = ee.Image(10).pow(tmp.select('VH').divide(10))

            # Output
            out = vh.select(['constant'], ['VH'])

            return out.set('system:time_start', tmp.get('system:time_start'))

        def tolin_dual(image):
            tmp = ee.Image(image)
            if dual_pol == True:
                lin = ee.Image(10).pow(tmp.divide(10))  # .select(['constant', 'constant_1'], ['VV', 'VH'])
            else:
                lin = ee.Image(10).pow(tmp.divide(10))  # .select(['constant'], ['VV'])

            return lin.set('system:time_start', tmp.get('system:time_start'))

        def todb(image):
            tmp = ee.Image(image)

            return ee.Image(10).multiply(tmp.log10()).set('system:time_start', tmp.get('system:time_start'))

        def applysnowmask(image):
            tmp = ee.Image(image)
            sdiff = tmp.select('VH').subtract(snowref)
            wetsnowmap = sdiff.lte(-2.6)  # .focal_mode(100, 'square', 'meters', 3)

            return (tmp.updateMask(wetsnowmap.eq(0)))

        def createAvg(image):
            # average pixels within the time-series foot print
            gee_roi = ee.Geometry.Point(self.lon, self.lat).buffer(self.buffer)
            #tmp = ee.Image(image).resample()

            tmp = ee.Image(image)


            # Conver to linear before averaging
            tmp = tmp.addBands(ee.Image(10).pow(tmp.select('VV').divide(10)))
            if dual_pol == True:
                tmp = tmp.addBands(ee.Image(10).pow(tmp.select('VH').divide(10)))
                tmp = tmp.select(['constant', 'constant_1', 'angle', 'lia'], ['VV', 'VH', 'angle', 'lia'])
            else:
                tmp = tmp.select(['constant', 'angle', 'lia'], ['VV', 'angle', 'lia'])

            reduced_img_data = tmp.reduceRegion(ee.Reducer.median(), gee_roi, 10)
            totcount = ee.Image(1).reduceRegion(ee.Reducer.count(), gee_roi, 10)
            pcount = tmp.reduceRegion(ee.Reducer.count(), gee_roi, 10)
            return ee.Feature(None, {'result': reduced_img_data, 'count': pcount, 'totcount': totcount})

        #  filter for track
        if dual_pol == True:
            gee_s1_track_fltd = filtered_collection.filterMetadata('relativeOrbitNumber_start', 'equals',
                                                                   track_nr).select(['VV', 'VH', 'angle'])
        else:
            gee_s1_track_fltd = filtered_collection.filterMetadata('relativeOrbitNumber_start', 'equals',
                                                                   track_nr).select(['VV', 'angle'])

        # compute lia
        lia_im = getLIA(gee_s1_track_fltd)
        # add as a band to all images
        gee_s1_track_fltd = gee_s1_track_fltd.map(lambda x: x.addBands(lia_im))
        # apply filters to collection
        gee_s1_track_fltd = gee_s1_track_fltd.map(miscMask)

        if varmask == True:
            # mask pixels with low temporal variability
            # compute temporal statistics
            gee_s1_ln = gee_s1_track_fltd.map(toln)
            k2vv = ee.Image(gee_s1_ln.select('VV').reduce(ee.Reducer.stdDev()))
            if dual_pol == True:
                k2vh = ee.Image(gee_s1_ln.select('VH').reduce(ee.Reducer.stdDev()))
                varmask = k2vv.gt(0.4).And(k2vh.gt(0.4))
            else:
                varmask = k2vv.gt(0.4)
            gee_s1_track_fltd = gee_s1_track_fltd.map(applyvarmask)

        if tempfilter == True:
            # apply a temporal speckle filter
            radius = 3
            units = 'pixels'
            gee_s1_linear = gee_s1_track_fltd.map(tolin_dual)
            gee_s1_dspckld_vv = self._multitemporalDespeckle(gee_s1_linear.select('VV'), radius, units,
                                                             {'before': -12, 'after': 12, 'units': 'month'})
            gee_s1_dspckld_vv = gee_s1_dspckld_vv.map(todb).select(['constant'], ['VV'])
            if dual_pol == True:
                gee_s1_dspckld_vh = self._multitemporalDespeckle(gee_s1_linear.select('VH'), radius, units,
                                                                 {'before': -12, 'after': 12, 'units': 'month'})
                gee_s1_dspckld_vh = gee_s1_dspckld_vh.map(todb).select(['constant'], ['VH'])
            if dual_pol == False:
                gee_s1_track_fltd = gee_s1_dspckld_vv.combine(gee_s1_track_fltd.select('angle')) \
                    .combine(gee_s1_track_fltd.select('lia'))
            else:
                gee_s1_track_fltd = gee_s1_dspckld_vv.combine(gee_s1_dspckld_vh) \
                    .combine(gee_s1_track_fltd.select('angle')) \
                    .combine(gee_s1_track_fltd.select('lia'))

        # if masksnow == True:
        #     # apply wet snow mask
        #     gee_s1_lin = gee_s1_track_fltd.select('VH').map(tolin)
        #     snowref = ee.Image(10).multiply(gee_s1_lin.reduce(ee.Reducer.intervalMean(5, 100)).log10())
        #     gee_s1_track_fltd = gee_s1_track_fltd.map(applysnowmask)

        # create average for buffer area - i.e. compute time-series
        gee_s1_mapped = gee_s1_track_fltd.map(createAvg)
        tmp = gee_s1_mapped.getInfo()
        print(tmp)
        # get vv
        vv_sig0 = 10 * np.log10(
            np.array([x['properties']['result']['VV'] for x in tmp['features']], dtype=np.float))

        ge_dates = np.array([dt.datetime.strptime(x['id'][17:32], '%Y%m%dT%H%M%S') for x in tmp['features']])

        if dual_pol == True:
            # get vh
            vh_sig0_lin = np.array([x['properties']['result']['VH'] for x in tmp['features']], dtype=np.float)
            vh_sig0 = 10 * np.log10(vh_sig0_lin)
            if masksnow == True:
                snowref = 10 * np.log10(np.mean(vh_sig0_lin[vh_sig0_lin > np.percentile(vh_sig0_lin, 5)]))
                snowmask = np.where(vh_sig0 - snowref > -2.6)
                vh_sig0 = vh_sig0[snowmask]
                vv_sig0 = vv_sig0[snowmask]
                ge_dates = ge_dates[snowmask]

        if returnLIA == True:
            # get lia
            lia = np.array([x['properties']['result']['lia'] for x in tmp['features']], dtype=np.float)
        else:
            # get angle
            lia = np.array([x['properties']['result']['angle'] for x in tmp['features']], dtype=np.float)

        # get val_count - i.e. compute the fraction of valid pixels within the footprint
        val_count = np.array(
            [np.float(x['properties']['count']['VV']) / np.float(x['properties']['totcount']['constant']) for x in
             tmp['features']], dtype=np.float)

        if masksnow == True:
            val_count = val_count[snowmask]

        if self.buffer <= 100:
            valid = np.where(val_count > 0.01)
        else:
            valid = np.where(val_count > 0.1)
        vv_sig0 = vv_sig0[valid]
        if dual_pol == True:
            vh_sig0 = vh_sig0[valid]
        lia = lia[valid]
        ge_dates = ge_dates[valid]

        if dual_pol == True:
            return (pd.DataFrame({'sig0': vv_sig0, 'sig02': vh_sig0, 'lia': lia}, index=ge_dates))
        else:
            return (pd.DataFrame({'sig0': vv_sig0, 'lia': lia}, index=ge_dates))

    def extr_LC(self, prod='Globcover'):
        # select prod='Globcover', 'Corine', 'USGS' (North America only for USGS)
        if prod == 'Globcover':
            lc_image = ee.Image("ESA/GLOBCOVER_L4_200901_200912_V2_3").select('landcover')
        elif prod == 'Corine':
            lc_image = ee.Image('users/felixgreifeneder/corine')
        elif prod == 'USGS':
            lc_image = ee.Image(ee.ImageCollection("USGS/NLCD").toList(100).get(-1))
        else:
            print('Unknown land-cover product')
            return

        roi = ee.Geometry.Point(self.lon, self.lat).buffer(self.buffer)
        lc = lc_image.reduceRegion(ee.Reducer.mode(), roi).getInfo()
        self.LC = lc['landcover']

    def extr_MODIS_MOD13Q1(self):
        # extract time-series of the MODIS product MOD13Q1

        def createAvg(image):
            gee_roi = ee.Geometry.Point(self.lon, self.lat).buffer(self.buffer)

            # mask image
            immask = image.select('SummaryQA').eq(ee.Image(0))
            image = image.updateMask(immask)

            reduced_img_data = image.reduceRegion(ee.Reducer.median(), gee_roi, 30)
            return ee.Feature(None, {'result': reduced_img_data})

        # load collection
        gee_l8_collection = ee.ImageCollection('MODIS/006/MOD13Q1')

        # filter collection
        gee_roi = ee.Geometry.Point(self.lon, self.lat).buffer(self.buffer)
        gee_l8_fltd = gee_l8_collection.filterBounds(gee_roi)

        # extract time series
        gee_l8_mpd = gee_l8_fltd.map(createAvg)
        tmp = gee_l8_mpd.getInfo()

        EVI = np.array([x['properties']['result']['EVI'] for x in tmp['features']], dtype=np.float)

        ge_dates = np.array([dt.datetime.strptime(x['id'], '%Y_%m_%d') for x in tmp['features']])

        valid = np.where(np.isfinite(EVI))

        # cut out invalid values
        EVI = EVI[valid]
        ge_dates = ge_dates[valid]

        return (pd.Series(EVI, index=ge_dates, name='EVI'))

    def extr_GLDAS_SM(self, yearlist=None):
        # get time series of GLDAS 0 to 10 cm soil moisture

        def createAvg(image):
            gee_roi = ee.Geometry.Point(self.lon, self.lat).buffer(self.buffer)

            reduced_img_data = image.reduceRegion(ee.Reducer.median(), gee_roi, 30, tileScale=4)
            return ee.Feature(None, {'result': reduced_img_data})

        if yearlist == None:
            # yearlist = range(1987,2018)
            yearlist = list(range(2011, 2018))

        SM_list = list()

        for iyear in yearlist:
            # ee.Reset()
            # ee.Initialize()
            print(iyear)
            # load collection
            if iyear < 2000:
                GLDAS_collection = ee.ImageCollection('NASA/GLDAS/V20/NOAH/G025/T3H').select('SoilMoi0_10cm_inst')
            else:
                GLDAS_collection = ee.ImageCollection('NASA/GLDAS/V021/NOAH/G025/T3H').select('SoilMoi0_10cm_inst')
            GLDAS_collection = GLDAS_collection.filterDate(str(iyear) + '-01-01', str(iyear) + '-12-31')
            GLDAS_collection = GLDAS_collection.filter(ee.Filter.calendarRange(16, 18, 'hour'))

            # clip
            roi = ee.Geometry.Point(self.lon, self.lat).buffer(self.buffer)
            GLDAS_collection = GLDAS_collection.map(lambda image: image.clip(roi))

            # extract time series
            time_series = GLDAS_collection.map(createAvg)
            tmp = time_series.getInfo()

            SM = np.array([x['properties']['result']['SoilMoi0_10cm_inst'] for x in tmp['features']], dtype=np.float)

            ge_dates = np.array([dt.datetime.strptime(x['id'], 'A%Y%m%d_%H%M') for x in tmp['features']])

            valid = np.where(np.isfinite(SM))

            # cut out invalid values
            SM = SM[valid]
            ge_dates = ge_dates[valid]

            SM_series = pd.Series(SM, index=ge_dates, copy=True, name='GLDAS')

            SM_list.append(SM_series)

        return (pd.concat(SM_list))

    def extr_GLDAS_date(self, date):
        doi = ee.Date(date)
        gldas = ee.ImageCollection("NASA/GLDAS/V021/NOAH/G025/T3H") \
            .select(['SoilMoi0_10cm_inst', 'CanopInt_inst']) \
            .filterDate(doi, doi.advance(3, 'hour'))

        gldas_img = ee.Image(gldas.first())
        roi = ee.Geometry.Point(self.lon, self.lat).buffer(self.buffer)
        try:
            return (gldas_img.reduceRegion(ee.Reducer.median(), roi, 50).getInfo())
        except:
            return {'SoilMoi0_10cm_inst': np.nan, 'CanopInt_inst': np.nan}

    def extr_terrain(self):
        roi = ee.Geometry.Point(self.lon, self.lat).buffer(self.buffer)
        elev = ee.Image("CGIAR/SRTM90_V4").reduceRegion(ee.Reducer.median(), roi).getInfo()
        aspe = ee.Terrain.aspect(ee.Image("CGIAR/SRTM90_V4")).reduceRegion(ee.Reducer.median(), roi).getInfo()
        slop = ee.Terrain.slope(ee.Image("CGIAR/SRTM90_V4")).reduceRegion(ee.Reducer.median(), roi).getInfo()
        self.ELEV = elev['elevation']
        self.ASPE = aspe['aspect']
        self.SLOP = slop['slope']

    def extr_S1(self,
                maskwinter=False,
                lcmask=False,
                globcover_mask=True,
                trackflt=None,
                masksnow=True,
                varmask=False,
                ssmcor=None,
                dual_pol=True,
                desc=True,
                asc=False,
                tempfilter=False,
                returnLIA=False):
        # extract filtered Sentinel-1 backscatter time-series
        def mask_lc(image):
            tmp = ee.Image(image)

            # load land cover info
            corine = ee.Image('users/felixgreifeneder/corine')

            # create lc mask
            valLClist = [10, 11, 12, 13, 18, 19, 20, 21, 26, 27, 28, 29]

            lcmask = corine.eq(valLClist[0]).bitwiseOr(corine.eq(valLClist[1])) \
                .bitwiseOr(corine.eq(valLClist[2])) \
                .bitwiseOr(corine.eq(valLClist[3])) \
                .bitwiseOr(corine.eq(valLClist[4])) \
                .bitwiseOr(corine.eq(valLClist[5])) \
                .bitwiseOr(corine.eq(valLClist[6])) \
                .bitwiseOr(corine.eq(valLClist[7])) \
                .bitwiseOr(corine.eq(valLClist[8])) \
                .bitwiseOr(corine.eq(valLClist[9])) \
                .bitwiseOr(corine.eq(valLClist[10])) \
                .bitwiseOr(corine.eq(valLClist[11]))

            tmp = tmp.updateMask(lcmask)

            return tmp

        def mask_lc_globcover(image):
            tmp = ee.Image(image)

            # load lc
            glbcvr = ee.Image("ESA/GLOBCOVER_L4_200901_200912_V2_3").select('landcover')

            valLClist = [11, 14, 20, 30, 120, 140, 150]

            lcmask = glbcvr.eq(valLClist[0]) \
                .bitwiseOr(glbcvr.eq(valLClist[1])) \
                .bitwiseOr(glbcvr.eq(valLClist[2])) \
                .bitwiseOr(glbcvr.eq(valLClist[3])) \
                .bitwiseOr(glbcvr.eq(valLClist[4])) \
                .bitwiseOr(glbcvr.eq(valLClist[5])) \
                .bitwiseOr(glbcvr.eq(valLClist[6]))

            tmp = tmp.updateMask(lcmask)

            return tmp

        def addRefSM(image):
            tmp = ee.Image(image)
            img_date = ee.Date(tmp.get('system:time_start'))
            RefSMtmp = RefSMcollection.filterDate(img_date.format('Y-M-d'))
            current_ssm = ee.ImageCollection(RefSMtmp).toList(10).get(0)

            out_image = tmp.addBands(ee.Image(current_ssm))

            return (out_image)

        def s1_simplyfy_date(image):
            return (image.set('system:time_start', ee.Date(ee.Date(image.get('system:time_start')).format('Y-M-d'))))

        def applyCorrelationMask(image):
            mask = ssm_vv_cor.select('correlation').gt(0.1)
            return (image.updateMask(mask))

            

        tic = timeit.default_timer()

        # load S1 data
        gee_s1_collection = ee.ImageCollection('COPERNICUS/S1_GRD')  # .map(setresample)

        # filter collection
        gee_roi = ee.Geometry.Point(self.lon, self.lat).buffer(self.buffer)

        gee_s1_filtered = gee_s1_collection.filter(ee.Filter.eq('instrumentMode', 'IW')) \
            .filterBounds(gee_roi) \
            .filter(ee.Filter.eq('platform_number', 'A')) \
            .filter(ee.Filter.listContains('transmitterReceiverPolarisation',
                                           'VV'))

        if desc == False:
            # Select only acquisition from ascending tracks
            gee_s1_filtered = gee_s1_filtered.filter(ee.Filter.eq('orbitProperties_pass', 'ASCENDING'))
            
        if asc == False:
            # Select only acquisition from descending tracks
            gee_s1_filtered = gee_s1_filtered.filter(ee.Filter.eq('orbitProperties_pass', 'DESCENDING'))

        if dual_pol == True:
            # select only acquisitions with VV AND VH
            gee_s1_filtered = gee_s1_filtered.filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))

        if maskwinter == True:
            # Mask winter based on the DOY
            gee_s1_filtered = gee_s1_filtered.filter(ee.Filter.dayOfYear(121, 304))

        if trackflt is not None:
            # Select only data from a specific S1 track
            if isinstance(trackflt, list):
                gee_s1_filtered = gee_s1_filtered.filter(
                    ee.Filter.inList(ee.List(trackflt), 'relativeOrbitNumber_start'))
            else:
                gee_s1_filtered = gee_s1_filtered.filter(ee.Filter.eq('relativeOrbitNumber_start', trackflt))

        if lcmask == True:
            # Mask pixels based on Corine land-cover
            gee_s1_filtered = gee_s1_filtered.map(mask_lc)
        if globcover_mask == True:
            # Mask pixels based on the Globcover land-cover classification
            gee_s1_filtered = gee_s1_filtered.map(mask_lc_globcover)

        if ssmcor is not None:
            # Mask pixels with a low correlation toe coarse resolution soil moisture
            # Mostly relevant if aggregating over a larger area
            RefSMlist = list()
            ssmcor = ssmcor.resample('D').mean().dropna()
            ssmcor = ssmcor.astype(np.float)
            for i in range(len(ssmcor)):
                ssm_img = ee.Image(ssmcor[i]).clip(gee_roi).float()
                ssm_img = ssm_img.set('system:time_start', ssmcor.index[i])
                RefSMlist.append(ssm_img)
            RefSMcollection = ee.ImageCollection(RefSMlist)

            # prepare the join
            s1_joined = gee_s1_filtered.map(s1_simplyfy_date)
            join_filter = ee.Filter.equals(leftField='system:time_start', rightField='system:time_start')
            simple_join = ee.Join.simple()
            s1_joined = simple_join.apply(s1_joined, RefSMcollection, join_filter)

            # create ssm reference SM, image collection
            s1_plus_RefSM = ee.ImageCollection(s1_joined.map(addRefSM, True))
            ssm_vv_cor = s1_plus_RefSM.select(['VV', 'constant']).reduce(ee.Reducer.pearsonsCorrelation())
            gee_s1_filtered = gee_s1_filtered.map(applyCorrelationMask)

        # get the track numbers
        tmp = gee_s1_filtered.getInfo()
        track_series = np.array([x['properties']['relativeOrbitNumber_start'] for x in tmp['features']])
        available_tracks = np.unique(track_series)

        print(('Extracting data from ' + str(len(available_tracks)) + ' Sentinel-1 tracks...'))
        print(available_tracks)
        # Creación diccionario
        out_dict = {}
        for track_nr in available_tracks:
            track_nr = track_nr.item()  # value corrected, .item() to convert most NumPy values to a native Python type
            out_dict[str(track_nr)] = self._s1_track_ts(gee_s1_filtered,
                                                             track_nr,
                                                             dual_pol,
                                                             varmask,
                                                             returnLIA,
                                                             masksnow,
                                                             tempfilter)
        print(out_dict)
        toc = timeit.default_timer()

        print(('Time-series extraction finished in ' + "{:10.2f}".format(toc - tic) + 'seconds'))

        self.S1TS = out_dict

    def extr_SM(self,
                tracknr=None,
                masksnow=False,
                tempfilter=True,
                calc_anomalies=False):

        if self.S1TS == None:
            # get S1 time-series
            self.extr_S1(maskwinter=False, lcmask=False, trackflt=tracknr,
                         masksnow=masksnow, tempfilter=tempfilter)

        s1_ts = self.S1TS

        # load SVR model
        modelpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'SVRmodel.p')
        MLmodel = pickle.load(open(modelpath, 'rb'), encoding='latin1')


        # extract land cover
        self.extr_LC()
        # extract terrain information
        self.extr_terrain()

        # check if one of the found tracks contains valid data
        empty = 0
        for track_id in list(s1_ts.keys()):
            if len(s1_ts[track_id]) == 0:
                empty = 1
        if empty == 1:
            print('No valid data was found')
            return None

        # create ts stack
        cntr = 0
        sm_estimated = list()
        anom_estimated = list()
        for track_id in list(s1_ts.keys()):
            # extract model attributes
            reg_model1 = (MLmodel[0], MLmodel[1])
            reg_model2 = (MLmodel[2], MLmodel[3])

            # calculate k1,...,kN and sig0m
            s1_ts[track_id].dropna(axis=0, how='any')
            temp_ts1 = s1_ts[track_id]['sig0']
            temp_ts2 = s1_ts[track_id]['sig02']
            temp_tslia = s1_ts[track_id]['lia']

            ts_length = len(temp_ts1)

            if ts_length < 10:
                print(('Estimation for track #' + str(track_id) + ' not possible - time-series too short'))
                continue

            temp_ts1_lin = np.power(10, temp_ts1 / 10.)
            temp_ts2_lin = np.power(10, temp_ts2 / 10.)
            meanVV = np.mean(temp_ts1_lin)
            meanVH = np.mean(temp_ts2_lin)
            k1VV = np.mean(np.log(temp_ts1_lin))
            k1VH = np.mean(np.log(temp_ts2_lin))
            k2VV = np.std(np.log(temp_ts1_lin))
            k2VH = np.std(np.log(temp_ts1_lin))

            # get gldas
            gldas_series = pd.Series(index=s1_ts[track_id].index)
            for i in gldas_series.index:
                gldas_tmp = self.extr_GLDAS_date(i.strftime('%Y-%m-%d'))
                gldas_series[i] = gldas_tmp['SoilMoi0_10cm_inst']

            # check for nans in the gldas time-series
            valid2 = np.where(np.isfinite(gldas_series) & np.isfinite(gldas_series))

            fmat_tmp1 = np.array([k1VV, k1VH, k2VV, k2VH, self.LC, np.mean(temp_tslia), self.ASPE,
                                  gldas_series.median()])  # , aspe, slop, elev, gldas_series.mean()])

            fmat_tmp2 = np.hstack(((temp_ts1_lin - meanVV).values.reshape(ts_length, 1),
                                   (temp_ts2_lin - meanVH).values.reshape(ts_length, 1),
                                   (gldas_series - gldas_series.mean()).values.reshape(ts_length, 1)))

            # apply masks to dates and fmat
            fmat_tmp2 = fmat_tmp2[valid2, :]
            dates = s1_ts[track_id].index[valid2]
            # fmat_tmp2 = fmat_tmp2[0]

            nn_model1 = reg_model1[0]
            nn_scaler1 = reg_model1[1]
            nn_model2 = reg_model2[0]
            nn_scaler2 = reg_model2[1]
            fvect1 = nn_scaler1.transform(fmat_tmp1.reshape(1, -1))
            fvect2 = nn_scaler2.transform(fmat_tmp2.squeeze())

            avg_ssm_estimated_tmp = nn_model1.predict(fvect1)
            diff_ssm_estimated_tmp = nn_model2.predict(fvect2)
            ssm_estimated_tmp = pd.Series((diff_ssm_estimated_tmp + avg_ssm_estimated_tmp) * 100, index=dates,
                                          name='S1')
            ssm_estimated_tmp = ssm_estimated_tmp[~ssm_estimated_tmp.index.duplicated(keep='first')]

            sm_estimated.append(ssm_estimated_tmp.copy())

            if calc_anomalies == True:
                # get GLDAS timeseries
                gldas_ts = self.extr_GLDAS_SM()

                # correct GLDAS for local variations
                gldas_ts_matched = df_match(ssm_estimated_tmp, gldas_ts, window=0.5)
                gldas_s1 = pd.concat([ssm_estimated_tmp, gldas_ts_matched['GLDAS']], axis=1, join='inner').dropna()
                lin_fit = LinearRegression()
                lin_fit.fit(gldas_s1['GLDAS'].values.reshape(-1, 1), gldas_s1['S1'].values)
                # calibrate GLDAS
                gldas_tmp = lin_fit.predict(gldas_ts.values.reshape(-1, 1))
                gldas_ts = pd.Series(gldas_tmp, index=gldas_ts.index)

                # calculate climatology
                gldas_clim = anomaly.calc_climatology(gldas_ts, moving_avg_clim=30)
                gldas_clim = pd.DataFrame(pd.Series(gldas_clim, name='S1'))
                # calculate anomaly
                anom_estimated_tmp = pd.Series(
                    [ssm_estimated_tmp[dateI] - gldas_clim['S1'][dateI.dayofyear] for dateI in ssm_estimated_tmp.index],
                    index=ssm_estimated_tmp.index,
                    dtype=np.float64)
                anom_estimated.append(anom_estimated_tmp.copy())

        sm_estimated = pd.concat(sm_estimated)
        sm_estimated.sort_index(inplace=True)
        if calc_anomalies == True:
            anom_estimated = pd.concat(anom_estimated)
            anom_estimated.sort_index(inplace=True)

        if calc_anomalies == False:
            return sm_estimated
        else:
            return pd.DataFrame({'S1SM': sm_estimated, 'ANOM': anom_estimated}, index=sm_estimated.index)

    def get_s1_dates(self, tracknr=None, dualpol=True):
        # get the S1 acquisition dates
        # load S1 data
        gee_s1_collection = ee.ImageCollection('COPERNICUS/S1_GRD')

        # construct roi
        roi = ee.Geometry.Point(self.lon, self.lat).buffer(self.buffer)

        # ASCENDING acquisitions
        gee_s1_filtered = gee_s1_collection.filter(ee.Filter.eq('instrumentMode', 'IW')) \
            .filterBounds(roi) \
            .filter(ee.Filter.eq('platform_number', 'A')) \
            .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')) \
            .filter(ee.Filter.eq('orbitProperties_pass', 'ASCENDING'))

        if dualpol == True:
            gee_s1_filtered = gee_s1_filtered.filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))

        if tracknr is not None:
            gee_s1_filtered = gee_s1_filtered.filter(ee.Filter.eq('relativeOrbitNumber_start', tracknr))

        # create a list of availalbel dates
        tmp = gee_s1_filtered.getInfo()
        tmp_ids = [x['properties']['system:index'] for x in tmp['features']]
        dates = np.array([dt.date(year=int(x[17:21]), month=int(x[21:23]), day=int(x[23:25])) for x in tmp_ids])
        # print (dates.size)
        return (dates)


class GEE_extent(object):
    """Class to create an interface with GEE for the extraction of arrays

        Attributes:
            minlon: minimum longitude in decimal degrees
            minlat: minumum latitude in decimal degress
            maxlon: maximum longitude in decimal degrees
            maxlat: maximum latitude in decimal degrees
            workdir: path to directory for exported files
            sampling: sampling of exported grids
        """

    def __init__(self, minlon, minlat, maxlon, maxlat, workdir, sampling=20):
        """Return a new GEE extent object"""
        ee.Reset()
        ee.Initialize()

        # construct roi
        roi = ee.Geometry.Polygon([[minlon, minlat], [minlon, maxlat],
                                   [maxlon, maxlat], [maxlon, minlat],
                                   [minlon, minlat]])

        self.roi = roi
        self.sampling = sampling
        self.workdir = workdir

        # Placeholders
        self.S1_SIG0_VV_db = None
        self.S1_SIG0_VH_db = None
        self.S1_ANGLE = None
        self.K1VV = None
        self.K1VH = None
        self.K2VV = None
        self.K2VH = None
        self.S1_DATE = None
        self.S1MEAN_VV = None
        self.S1MEAN_VH = None
        self.S1STD_VV = None
        self.S1STD_VH = None
        self.S1_LIA = None
        self.ESTIMATED_SM = None
        self.GLDAS_IMG = None
        self.GLDAS_MEAN = None
        self.LAND_COVER = None
        self.TERRAIN = None

    def _multitemporalDespeckle(self, images, radius, units, opt_timeWindow=None):
        """Function for multi-temporal  """

        def mapMeanSpace(i):
            reducer = ee.Reducer.mean()
            kernel = ee.Kernel.square(radius, units)
            mean = i.reduceNeighborhood(reducer, kernel).rename(bandNamesMean)
            ratio = i.divide(mean).rename(bandNamesRatio)
            return (i.addBands(mean).addBands(ratio))

        if opt_timeWindow == None:
            timeWindow = dict(before=-3, after=3, units='month')
        else:
            timeWindow = opt_timeWindow

        bandNames = ee.Image(images.first()).bandNames()
        bandNamesMean = bandNames.map(lambda b: ee.String(b).cat('_mean'))
        bandNamesRatio = bandNames.map(lambda b: ee.String(b).cat('_ratio'))

        # compute spatial average for all images
        meanSpace = images.map(mapMeanSpace)

        # computes a multi-temporal despeckle function for a single image

        def multitemporalDespeckleSingle(image):
            t = image.date()
            fro = t.advance(ee.Number(timeWindow['before']), timeWindow['units'])
            to = t.advance(ee.Number(timeWindow['after']), timeWindow['units'])

            meanSpace2 = ee.ImageCollection(meanSpace).select(bandNamesRatio).filterDate(fro, to) \
                .filter(ee.Filter.eq('relativeOrbitNumber_start', image.get('relativeOrbitNumber_start')))

            b = image.select(bandNamesMean)

            return (b.multiply(meanSpace2.sum()).divide(meanSpace2.count()).rename(bandNames)).set('system:time_start',
                                                                                                   image.get(
                                                                                                       'system:time_start'))

        return meanSpace.map(multitemporalDespeckleSingle)

    def get_S1(self, year, month, day,
               tempfilter=True,
               tempfilter_radius=7,
               applylcmask=False,
               mask_globcover=True,
               dualpol=True,
               trackflt=None,
               maskwinter=False,
               masksnow=True,
               explicit_t_mask=None,
               ascending=False,
               descending=True,
               maskLIA=True):
        """Retrieve the S1 image for a given day from GEE and apply specific filters.
           Assigns outputs to respective instance attributes

        """

        def computeLIA(image):
            # comput the local incidence angle (LIA) based on the srtm and the s1 viewing angle
            # get the srtm
            srtm = ee.Image("USGS/SRTMGL1_003")
            srtm_slope = ee.Terrain.slope(srtm)
            srtm_aspect = ee.Terrain.aspect(srtm)
            # get the S1 incidence angle
            inc = ee.Image(image).select('angle')
            # comput the LIA
            s = srtm_slope.multiply(ee.Image.constant(277).subtract(srtm_aspect).multiply(math.pi / 180).cos())
            lia = inc.subtract(ee.Image.constant(90).subtract(ee.Image.constant(90).subtract(s))).abs()
            # add band to current image
            return image.addBands(lia.select(['angle'], ['lia']).reproject(srtm.projection()))

        def maskterrain(image):
            # mask for terrain, local incidence angle and high and low backscatter
            tmp = ee.Image(image)
            # srtm dem
            if maskLIA == False:
                gee_srtm = ee.Image("USGS/SRTMGL1_003")
                gee_srtm_slope = ee.Terrain.slope(gee_srtm)
                mask = gee_srtm_slope.lt(20)
            else:
                lia = tmp.select('lia')
                mask = lia.gt(20).bitwiseAnd(lia.lt(45))
            mask2 = tmp.lt(0).bitwiseAnd(tmp.gt(-25))
            mask = mask.bitwiseAnd(mask2)
            tmp = tmp.updateMask(mask)

            return (tmp)

        def masklc(image):
            # load land cover info
            corine = ee.Image('users/felixgreifeneder/corine')

            # create lc mask
            valLClist = [10, 11, 12, 13, 18, 19, 20, 21, 26, 27, 28, 29]

            lcmask = corine.eq(valLClist[0]).bitwiseOr(corine.eq(valLClist[1])) \
                .bitwiseOr(corine.eq(valLClist[2])) \
                .bitwiseOr(corine.eq(valLClist[3])) \
                .bitwiseOr(corine.eq(valLClist[4])) \
                .bitwiseOr(corine.eq(valLClist[5])) \
                .bitwiseOr(corine.eq(valLClist[6])) \
                .bitwiseOr(corine.eq(valLClist[7])) \
                .bitwiseOr(corine.eq(valLClist[8])) \
                .bitwiseOr(corine.eq(valLClist[9])) \
                .bitwiseOr(corine.eq(valLClist[10])) \
                .bitwiseOr(corine.eq(valLClist[11]))

            tmp = ee.Image(image)

            tmp = tmp.updateMask(lcmask)
            return (tmp)

        def mask_lc_globcover(image):

            tmp = ee.Image(image)

            # load lc
            glbcvr = ee.Image("ESA/GLOBCOVER_L4_200901_200912_V2_3").select('landcover')

            valLClist = [11, 14, 20, 30, 40, 50, 60, 70, 90, 100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 210, 220, 230]

            lcmask = glbcvr.eq(valLClist[0]) \
                .bitwiseOr(glbcvr.eq(valLClist[1])) \
                .bitwiseOr(glbcvr.eq(valLClist[2])) \
                .bitwiseOr(glbcvr.eq(valLClist[3])) \
                .bitwiseOr(glbcvr.eq(valLClist[4])) \
                .bitwiseOr(glbcvr.eq(valLClist[5])) \
                .bitwiseOr(glbcvr.eq(valLClist[6])) \
                .bitwiseOr(glbcvr.eq(valLClist[7])) \
                .bitwiseOr(glbcvr.eq(valLClist[8])) \
                .bitwiseOr(glbcvr.eq(valLClist[9])) \
                .bitwiseOr(glbcvr.eq(valLClist[10])) \
                .bitwiseOr(glbcvr.eq(valLClist[11])) \
                .bitwiseOr(glbcvr.eq(valLClist[12])) \
                .bitwiseOr(glbcvr.eq(valLClist[13])) \
                .bitwiseOr(glbcvr.eq(valLClist[14])) \
                .bitwiseOr(glbcvr.eq(valLClist[15])) \
                .bitwiseOr(glbcvr.eq(valLClist[16])) \
                .bitwiseOr(glbcvr.eq(valLClist[17])) \
                .bitwiseOr(glbcvr.eq(valLClist[18])) \
                .bitwiseOr(glbcvr.eq(valLClist[19])) \
                .bitwiseOr(glbcvr.eq(valLClist[20])) \
                .bitwiseOr(glbcvr.eq(valLClist[21])) \
                .bitwiseOr(glbcvr.eq(valLClist[22]))
            

            tmp = tmp.updateMask(lcmask)

            return tmp

        def setresample(image):
            image = image.resample()
            return (image)

        def toln(image):

            tmp = ee.Image(image)

            # Convert to linear
            vv = ee.Image(10).pow(tmp.select('VV').divide(10))
            if dualpol == True:
                vh = ee.Image(10).pow(tmp.select('VH').divide(10))

            # Convert to ln
            out = vv.log()
            if dualpol == True:
                out = out.addBands(vh.log())
                out = out.select(['constant', 'constant_1'], ['VV', 'VH'])
            else:
                out = out.select(['constant'], ['VV'])

            return out.set('system:time_start', tmp.get('system:time_start'))

        def tolin(image):

            tmp = ee.Image(image)

            # Covert to linear
            vv = ee.Image(10).pow(tmp.select('VV').divide(10))
            if dualpol == True:
                vh = ee.Image(10).pow(tmp.select('VH').divide(10))

            # Convert to
            if dualpol == True:
                out = vv.addBands(vh)
                out = out.select(['constant', 'constant_1'], ['VV', 'VH'])
            else:
                out = vv.select(['constant'], ['VV'])

            return out.set('system:time_start', tmp.get('system:time_start'))

        def todb(image):

            tmp = ee.Image(image)

            return ee.Image(10).multiply(tmp.log10()).set('system:time_start', tmp.get('system:time_start'))

        def applysnowmask(image):

            tmp = ee.Image(image)
            sdiff = tmp.select('VH').subtract(snowref)
            wetsnowmap = sdiff.lte(-2.6).focal_mode(100, 'square', 'meters', 3)

            return (tmp.updateMask(wetsnowmap.eq(0)))

        def projectlia(image):
            tmp = ee.Image(image)
            trgtprj = tmp.select('VV').projection()
            tmp = tmp.addBands(tmp.select('angle').reproject(trgtprj), ['angle'], True)
            return (tmp)

        def apply_explicit_t_mask(image):

            t_mask = ee.Image('users/felixgreifeneder/' + explicit_t_mask)
            mask = t_mask.eq(0)
            return (image.updateMask(mask))

        ee.Reset()
        ee.Initialize()

        # load S1 data
        gee_s1_collection = ee.ImageCollection('COPERNICUS/S1_GRD')

        # Filter the image collection
        gee_s1_filtered = gee_s1_collection.filter(ee.Filter.eq('instrumentMode', 'IW')) \
            .filterBounds(self.roi) \
            .filter(ee.Filter.eq('platform_number', 'A')) \
            .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))

        if ascending == True:
            # Consider only image from ascending orbits
            gee_s1_filtered = gee_s1_filtered.filter(ee.Filter.eq('orbitProperties_pass', 'ASCENDING'))
        
        if descending == True:
            # Consider only image from descending orbits
            gee_s1_filtered = gee_s1_filtered.filter(ee.Filter.eq('orbitProperties_pass', 'DESCENDING'))

        if dualpol == True:
            # Consider only dual-pol scenes
            gee_s1_filtered = gee_s1_filtered.filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))

        if trackflt is not None:
            # Specify track
            gee_s1_filtered = gee_s1_filtered.filter(ee.Filter.eq('relativeOrbitNumber_start', trackflt))

        if maskwinter == True:
            # Mask winter based on DOY
            gee_s1_filtered = gee_s1_filtered.filter(ee.Filter.dayOfYear(121, 304))

        # add LIA
        if maskLIA == True:
            # compute the local incidence angle if it shall be used for masking
            gee_s1_filtered = gee_s1_filtered.map(computeLIA)
            s1_lia = gee_s1_filtered.select('lia')
        else:
            s1_lia = None

        s1_angle = gee_s1_filtered.select('angle')

        if applylcmask == True:
            # apply land-cover mask based on Corine
            gee_s1_filtered = gee_s1_filtered.map(masklc)
        if mask_globcover == True:
            # apply land-cover mask based on globcover
            gee_s1_filtered = gee_s1_filtered.map(mask_lc_globcover)

        # Enable bilinear resampling (instead of NN)
        gee_s1_filtered = gee_s1_filtered.map(setresample)

        if explicit_t_mask == None:
            # apply masking based on the terraing (LIA)
            gee_s1_filtered = gee_s1_filtered.map(maskterrain)
        else:
            # apply specific terrain mask
            gee_s1_filtered = gee_s1_filtered.map(apply_explicit_t_mask)

        if masksnow == True:
            # automatic wet snow masking
            gee_s1_linear_vh = gee_s1_filtered.map(tolin).select('VH')
            snowref = ee.Image(10).multiply(gee_s1_linear_vh.reduce(ee.Reducer.intervalMean(5, 100)).log10())
            gee_s1_filtered = gee_s1_filtered.map(applysnowmask)

        #### SHOULD BE IF STATEMENT HERE

        # create a list of availalbel dates
        tmp = gee_s1_filtered.getInfo()
        tmp_ids = [x['properties']['system:index'] for x in tmp['features']]
        

        dates = np.array([dt.date(year=int(x[17:21]), month=int(x[21:23]), day=int(x[23:25])) for x in tmp_ids])


        # find the closest acquisitions
        doi = dt.date(year=year, month=month, day=day)
        doi_index = np.argmin(np.abs(dates - doi))
        date_selected = dates[doi_index]

        # filter imagecollection for respective date
        gee_s1_drange = gee_s1_filtered.filterDate(date_selected.strftime('%Y-%m-%d'),
                                                   (date_selected + dt.timedelta(days=1)).strftime('%Y-%m-%d'))
        s1_angle_drange = s1_angle.filterDate(date_selected.strftime('%Y-%m-%d'),
                                              (date_selected + dt.timedelta(days=1)).strftime('%Y-%m-%d'))
        if maskLIA == True:
            s1_lia_drange = s1_lia.filterDate(date_selected.strftime('%Y-%m-%d'),
                                              (date_selected + dt.timedelta(days=1)).strftime('%Y-%m-%d'))
        if gee_s1_drange.size().getInfo() > 1:
            if maskLIA == True:
                s1_lia = s1_lia_drange.mosaic()
            s1_angle = s1_angle_drange.mosaic()
            s1_sig0 = gee_s1_drange.mosaic()
            s1_lia = ee.Image(s1_lia.copyProperties(s1_lia_drange.first()))
            s1_sig0 = ee.Image(s1_sig0.copyProperties(gee_s1_drange.first()))
        else:
            s1_sig0 = ee.Image(gee_s1_drange.first())
            s1_angle = ee.Image(s1_angle_drange.first())
            s1_lia = ee.Image(s1_lia_drange.first())

        # fetch image from image collection
        # get the track number
        s1_sig0_info = s1_sig0.getInfo()
        track_nr = s1_sig0_info['properties']['relativeOrbitNumber_start']

        # only uses images of the same track
        gee_s1_filtered = gee_s1_filtered.filterMetadata('relativeOrbitNumber_start', 'equals', track_nr)

        if tempfilter == True:
            # despeckle
            radius = tempfilter_radius
            units = 'pixels'
            gee_s1_linear = gee_s1_filtered.map(tolin)
            gee_s1_dspckld_vv = self._multitemporalDespeckle(gee_s1_linear.select('VV'), radius, units,
                                                             {'before': -12, 'after': 12, 'units': 'month'})
            gee_s1_dspckld_vv = gee_s1_dspckld_vv.map(todb)
            gee_s1_fltrd_vv = gee_s1_dspckld_vv.filterDate(date_selected.strftime('%Y-%m-%d'),
                                                           (date_selected + dt.timedelta(days=1)).strftime('%Y-%m-%d'))
            s1_sig0_vv = gee_s1_fltrd_vv.mosaic()

            if dualpol == True:
                gee_s1_dspckld_vh = self._multitemporalDespeckle(gee_s1_linear.select('VH'), radius, units,
                                                                 {'before': -12, 'after': 12, 'units': 'month'})
                gee_s1_dspckld_vh = gee_s1_dspckld_vh.map(todb)
                gee_s1_fltrd_vh = gee_s1_dspckld_vh.filterDate(date_selected.strftime('%Y-%m-%d'),
                                                               (date_selected + dt.timedelta(days=1)).strftime(
                                                                   '%Y-%m-%d'))
                s1_sig0_vh = gee_s1_fltrd_vh.mosaic()

            if dualpol == True:
                s1_sig0 = s1_sig0_vv.addBands(s1_sig0_vh).select(['constant', 'constant_1'], ['VV', 'VH'])
            else:
                s1_sig0 = s1_sig0_vv.select(['constant'], ['VV'])

        # extract information
        s1_sig0_vv = s1_sig0.select('VV')
        s1_sig0_vv = s1_sig0_vv.clip(self.roi)
        if dualpol == True:
            s1_sig0_vh = s1_sig0.select('VH')
            s1_sig0_vh = s1_sig0_vh.clip(self.roi)

        gee_s1_ln = gee_s1_filtered.map(toln)
        gee_s1_lin = gee_s1_filtered.map(tolin)
        k1vv = ee.Image(gee_s1_ln.select('VV').mean()).clip(self.roi)
        k2vv = ee.Image(gee_s1_ln.select('VV').reduce(ee.Reducer.stdDev())).clip(self.roi)
        mean_vv = ee.Image(gee_s1_lin.select('VV').mean()).clip(self.roi)
        std_vv = ee.Image(gee_s1_lin.select('VV').reduce(ee.Reducer.stdDev())).clip(self.roi)

        if dualpol == True:
            k1vh = ee.Image(gee_s1_ln.select('VH').mean()).clip(self.roi)
            k2vh = ee.Image(gee_s1_ln.select('VH').reduce(ee.Reducer.stdDev())).clip(self.roi)
            mean_vh = ee.Image(gee_s1_lin.select('VH').mean()).clip(self.roi)
            std_vh = ee.Image(gee_s1_lin.select('VH').reduce(ee.Reducer.stdDev())).clip(self.roi)

        # export
        if dualpol == False:
            self.S1_SIG0_VV_db = s1_sig0_vv
            self.S1_ANGLE = s1_angle
            self.K1VV = k1vv
            self.K2VV = k2vv
            self.S1_DATE = date_selected
        else:
            self.S1_SIG0_VV_db = s1_sig0_vv
            self.S1_SIG0_VH_db = s1_sig0_vh
            self.S1_ANGLE = s1_angle
            self.K1VV = k1vv
            self.K1VH = k1vh
            self.K2VV = k2vv
            self.K2VH = k2vh
            self.S1_DATE = date_selected
            self.S1MEAN_VV = mean_vv
            self.S1MEAN_VH = mean_vh
            self.S1STD_VV = std_vv
            self.S1STD_VH = std_vh

        if maskLIA == True:
            self.S1_LIA = s1_lia

    def estimate_SM(self):
        # load SVR model

        warnings.simplefilter(action='ignore', category=FutureWarning) # Hide the warnings
        warnings.simplefilter(action='ignore', category=UserWarning)

# --------------------------------------------------------------------
# OLD PART OF LOADING THE MODEL
#         MLmodel_tuple = pickle.load(open(modelpath, 'rb'), encoding='latin1') # Changed line to open pickle file pickled in older version


#        MLmodel1 = {'SVRmodel': MLmodel_tuple[0], 'scaler': MLmodel_tuple[1]}
#        MLmodel2 = {'SVRmodel': MLmodel_tuple[2], 'scaler': MLmodel_tuple[3]}

        # create parameter images
#        alpha1 = [ee.Image(MLmodel1['SVRmodel'].best_estimator_.dual_coef_[0][i]) for i in
#                 range(len(MLmodel1['SVRmodel'].best_estimator_.dual_coef_[0]))]
#        gamma1 = ee.Image(-MLmodel1['SVRmodel'].best_estimator_.gamma)
#        intercept1 = ee.Image(MLmodel1['SVRmodel'].best_estimator_.intercept_[0])
# --------------------------------------------------------------------

# --------------------------------------------------------------------
# new part of loading the model

        # load the numpy pickle file saved with np.save
        new_model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model_dict.npy')
        model_param = np.load(new_model_path, allow_pickle=True).item()
    
        # recunstruct the parameters used in classification
        #alpha1 = [ee.Image(MLmodel1['SVRmodel'].best_estimator_.dual_coef_[0][i]) for i in
        #         range(len(MLmodel1['SVRmodel'].best_estimator_.dual_coef_[0]))]
        alpha1 = [ee.Image(model_param['model1']['alpha_array'][i]) for i in
                 range(len(model_param['model1']['alpha_array']))]
        gamma1 = ee.Image(-model_param['model1']['gamma'])
        intercept1 = ee.Image(model_param['model1']['intercept'])
        sup_vectors1 = model_param['model1']['support_vectors']
# --------------------------------------------------------------------
        
        # support vectors stack
        # sup_vectors1 = MLmodel1['SVRmodel'].best_estimator_.support_vectors_
        n_vectors1 = sup_vectors1.shape[0]
        n_features1 = 8

        tmp_list = [ee.Image(sup_vectors1[0, i]) for i in range(n_features1)]

        sup_image1 = ee.Image.cat(tmp_list).select(['constant', 'constant_1', 'constant_2',
                                                    'constant_3', 'constant_4', 'constant_5',
                                                    'constant_6', 'constant_7'],
                                                   ['VVk1', 'VHk1', 'VVk2', 'VHk2',
                                                    'lc', 'lia', 'aspect', 'gldas_mean'])
        sup_list1 = [sup_image1]

        for i in range(1, n_vectors1):
            tmp_list = [ee.Image(sup_vectors1[i, j]) for j in range(n_features1)]

            sup_image1 = ee.Image.cat(tmp_list).select(['constant', 'constant_1', 'constant_2',
                                                        'constant_3', 'constant_4', 'constant_5',
                                                        'constant_6', 'constant_7'],
                                                       ['VVk1', 'VHk1', 'VVk2', 'VHk2',
                                                        'lc', 'lia', 'aspect', 'gldas_mean'])
            sup_list1.append(sup_image1)

        # create estimation stack
        vv = self.S1_SIG0_VV_db
        k1_vv = self.K1VV
        k1_vh = self.K1VH
        k2_vv = self.K2VV
        k2_vh = self.K2VH
        lia = self.S1_ANGLE.rename(['lia'])
        aspect = self.TERRAIN[2].rename(['aspect'])
        slope = self.TERRAIN[1].rename(['slope'])
        height = self.TERRAIN[0].rename(['height'])
        gldas_img = self.GLDAS_IMG
        gldas_mean = self.GLDAS_MEAN
        lc = self.LAND_COVER

        input_image1 = ee.Image([k1_vv.toFloat(),
                                 k1_vh.toFloat(),
                                 k2_vv.toFloat(),
                                 k2_vh.toFloat(),
                                 lc.toFloat(),
                                 lia.toFloat(),
                                 aspect.toFloat(),
                                 gldas_mean.toFloat()])
        ipt_img_mask1 = input_image1.mask().reduce(ee.Reducer.allNonZero())
        S1mask = vv.mask()
        zeromask = input_image1.neq(ee.Image(0)).reduce(ee.Reducer.allNonZero())
        combined_mask = S1mask.And(zeromask).And(ipt_img_mask1)

        input_image1 = input_image1.updateMask(ee.Image(combined_mask))

        # scale the estimation image
        # replace
        #scaling_std_img1 = ee.Image(
        #    [ee.Image(MLmodel1['scaler'].scale_[i].astype(np.float)) for i in range(n_features1)])
        scaling_std_img1 = ee.Image(
            [ee.Image(model_param['model1']['scaler_scale'][i].astype(np.float)) for i in range(n_features1)])

        scaling_std_img1 = scaling_std_img1.select(['constant', 'constant_1', 'constant_2',
                                                    'constant_3', 'constant_4', 'constant_5',
                                                    'constant_6', 'constant_7'],
                                                   ['VVk1', 'VHk1', 'VVk2', 'VHk2',
                                                    'lc', 'lia', 'aspect', 'gldas_mean'])

        #scaling_mean_img1 = ee.Image(
        #    [ee.Image(MLmodel1['scaler'].center_[i].astype(np.float)) for i in range(n_features1)])
        ### REPLACEMENT ###
        scaling_mean_img1 = ee.Image(
            [ee.Image(model_param['model1']['scaler_center'][i].astype(np.float)) for i in range(n_features1)])

        scaling_mean_img1 = scaling_mean_img1.select(['constant', 'constant_1', 'constant_2',
                                                      'constant_3', 'constant_4', 'constant_5',
                                                      'constant_6', 'constant_7'],
                                                     ['VVk1', 'VHk1', 'VVk2', 'VHk2',
                                                      'lc', 'lia', 'aspect', 'gldas_mean'])

        input_image_scaled1 = input_image1.subtract(scaling_mean_img1).divide(scaling_std_img1)

        k_x1x2_1 = [sup_list1[i].subtract(input_image_scaled1) \
                        .pow(ee.Image(2)) \
                        .reduce(ee.Reducer.sum()) \
                        .sqrt() \
                        .pow(ee.Image(2)) \
                        .multiply(ee.Image(gamma1)) \
                        .exp() for i in range(n_vectors1)]

        alpha_times_k1 = [ee.Image(alpha1[i].multiply(k_x1x2_1[i])) for i in range(n_vectors1)]

        #print(n_vectors1)

        alpha_times_k_sum_1 = ee.ImageCollection(alpha_times_k1).reduce(ee.Reducer.sum())
        # alpha_times_k_sum = alpha_times_k.reduce(ee.Reducer.sum())

        # print(alpha_times_k_sum.getInfo())

        estimated_smc_average = alpha_times_k_sum_1.add(intercept1)

        # estimate relative smc

        # create parameter images
        #alpha2 = [ee.Image(MLmodel2['SVRmodel'].best_estimator_.dual_coef_[0][i]) for i in
        #          range(len(MLmodel2['SVRmodel'].best_estimator_.dual_coef_[0]))]
        #gamma2 = ee.Image(-MLmodel2['SVRmodel'].best_estimator_.gamma)
        #intercept2 = ee.Image(MLmodel2['SVRmodel'].best_estimator_.intercept_[0])
        
        ### REPLACEMENT####
        alpha2 = [ee.Image(model_param['model2']['alpha_array'][i]) for i in
                  range(len(model_param['model2']['alpha_array']))]
        gamma2 = ee.Image(-model_param['model2']['gamma'])
        intercept2 = ee.Image(model_param['model2']['intercept'])
        sup_vectors2 = model_param['model2']['support_vectors']
        
        # support vectors stack
        #sup_vectors2 = MLmodel2['SVRmodel'].best_estimator_.support_vectors_
        n_vectors2 = sup_vectors2.shape[0]
        n_features2 = 3

        tmp_list = [ee.Image(sup_vectors2[0, i]) for i in range(n_features2)]

        sup_image2 = ee.Image.cat(tmp_list).select(['constant', 'constant_1', 'constant_2'],
                                                   ['relVV', 'relVH', 'gldas'])
        sup_list2 = [sup_image2]

        for i in range(1, n_vectors2):
            tmp_list = [ee.Image(sup_vectors2[i, j]) for j in range(n_features2)]

            sup_image2 = ee.Image.cat(tmp_list).select(['constant', 'constant_1', 'constant_2'],
                                                       ['relVV', 'relVH', 'gldas'])
            sup_list2.append(sup_image2)

        # create estimation stack
        vv = self.S1_SIG0_VV_db
        vh = self.S1_SIG0_VH_db
        vv_mean = self.S1MEAN_VV
        vh_mean = self.S1MEAN_VH
        vv_std = self.S1STD_VV
        vh_std = self.S1STD_VH

        vv_lin = ee.Image(10).pow(vv.divide(10)).rename(['relVV'])
        vh_lin = ee.Image(10).pow(vh.divide(10)).rename(['relVH'])

        input_image2 = ee.Image([vv_lin.subtract(vv_mean).toFloat(),
                                 vh_lin.subtract(vh_mean).toFloat(),
                                 gldas_img.subtract(gldas_mean).rename(['gldas']).toFloat()])
        ipt_img_mask2 = input_image2.mask().reduce(ee.Reducer.allNonZero())
        S1mask = vv.mask()
        zeromask = input_image2.neq(ee.Image(0)).reduce(ee.Reducer.allNonZero())
        combined_mask = S1mask.And(zeromask).And(ipt_img_mask2)

        input_image2 = input_image2.updateMask(ee.Image(combined_mask))

        # scale the estimation image
        scaling_std_img2 = ee.Image(
            [ee.Image(model_param['model2']['scaler_scale'][i].astype(np.float)) for i in range(n_features2)])

        scaling_std_img2 = scaling_std_img2.select(['constant', 'constant_1', 'constant_2'],
                                                   ['relVV', 'relVH', 'gldas'])

        scaling_mean_img2 = ee.Image(
            [ee.Image(model_param['model2']['scaler_center'][i].astype(np.float)) for i in range(n_features2)])

        scaling_mean_img2 = scaling_mean_img2.select(['constant', 'constant_1', 'constant_2'],
                                                     ['relVV', 'relVH', 'gldas'])

        input_image_scaled2 = input_image2.subtract(scaling_mean_img2).divide(scaling_std_img2)

        k_x1x2_2 = [sup_list2[i].subtract(input_image_scaled2) \
                        .pow(ee.Image(2)) \
                        .reduce(ee.Reducer.sum()) \
                        .sqrt() \
                        .pow(ee.Image(2)) \
                        .multiply(ee.Image(gamma2)) \
                        .exp() for i in range(n_vectors2)]

        alpha_times_k2 = [ee.Image(alpha2[i].multiply(k_x1x2_2[i])) for i in range(n_vectors2)]

        #print(n_vectors2)

        alpha_times_k_sum_2 = ee.ImageCollection(alpha_times_k2).reduce(ee.Reducer.sum())

        estimated_smc_relative = alpha_times_k_sum_2.add(intercept2)

        estimated_smc = estimated_smc_average.add(estimated_smc_relative).multiply(100).round().int8()

        # mask negative values
        estimated_smc = estimated_smc.updateMask(estimated_smc.gt(0))
        self.ESTIMATED_SM = estimated_smc

    def get_S1_dates(self, tracknr=None, dualpol=True):
        # load S1 data
        gee_s1_collection = ee.ImageCollection('COPERNICUS/S1_GRD')

        # DESCENDING acquisitions
        gee_s1_filtered = gee_s1_collection\
            .filter(ee.Filter.eq('instrumentMode', 'IW')) \
            .filterBounds(self.roi) \
            .filter(ee.Filter.eq('platform_number', 'A')) \
            .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')) \
            .filter(ee.Filter.eq('orbitProperties_pass', 'DESCENDING'))

        if dualpol == True:
            gee_s1_filtered = gee_s1_filtered.filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))

        if tracknr is not None:
            gee_s1_filtered = gee_s1_filtered.filter(ee.Filter.eq('relativeOrbitNumber_start', tracknr))

        # create a list of availalbel dates
        tmp = gee_s1_filtered.getInfo()
        tmp_ids = [x['properties']['system:index'] for x in tmp['features']]
        dates = np.array([dt.date(year=int(x[17:21]), month=int(x[21:23]), day=int(x[23:25])) for x in tmp_ids])

        return dates

    def get_gldas(self, date=None):
        # get GLDAS, date can be passed as a string or copied from the extracted S1 scene
        if date is None:
            doi = ee.Date(self.S1_DATE.strftime(format='%Y-%m-%d'))

        gldas_mean = ee.ImageCollection("NASA/GLDAS/V021/NOAH/G025/T3H") \
            .select('SoilMoi0_10cm_inst') \
            .filterDate('2014-10-01', '2018-01-22').reduce(ee.Reducer.mean())

        gldas_mean = ee.Image(gldas_mean).resample().clip(self.roi)

        gldas = ee.ImageCollection("NASA/GLDAS/V021/NOAH/G025/T3H") \
            .select('SoilMoi0_10cm_inst') \
            .filterDate(doi, doi.advance(3, 'hour'))

        if gldas.size().getInfo() == 0:
            #print('No GLDAS product for specified date')
            gldas_test = ee.ImageCollection("NASA/GLDAS/V021/NOAH/G025/T3H") \
                .select('SoilMoi0_10cm_inst')
            last_gldas = gldas_test.aggregate_max('system:index').getInfo()
            #print(('ID of latest available product: ' + last_gldas))
            self.GLDAS_IMG = None
            self.GLDAS_MEAN = None
            return

        gldas_img = ee.Image(gldas.first()).resample().clip(self.roi)

        try:
            self.GLDAS_IMG = gldas_img
            self.GLDAS_MEAN = gldas_mean
        except:
            return None

    def get_globcover(self):
        # get the globcover land-cover classification
        globcover_image = ee.Image("ESA/GLOBCOVER_L4_200901_200912_V2_3")
        land_cover = globcover_image.select('landcover').clip(self.roi)
        self.LAND_COVER = land_cover

    def get_terrain(self):
        # get SRTM data
        elev = ee.Image("CGIAR/SRTM90_V4").select('elevation').clip(self.roi)
        aspe = ee.Terrain.aspect(ee.Image("CGIAR/SRTM90_V4")).select('aspect').clip(self.roi)
        slop = ee.Terrain.slope(ee.Image("CGIAR/SRTM90_V4")).select('slope').clip(self.roi)
        self.TERRAIN = (elev, aspe, slop)

    def GEE_2_disk(self, outdir=None, raster='ESTIMATED_SM', name='SM', timeout=True):
        # Download GEE rasters - specify raster as string

        geds = self.__getattribute__(raster)

        if outdir is None:
            outdir = self.workdir
        success = 1
        file_exp = ee.batch.Export.image.toDrive(image=geds, description='fileexp' + name,
                                                 fileNamePrefix=name, scale=self.sampling,
                                                 region=self.roi.getInfo()['coordinates'],
                                                 maxPixels=1000000000000)

        file_exp.start()

        start = time.time()
        success = 1

        while (file_exp.active() == True):
            time.sleep(2)
            if timeout == True and (time.time() - start) > 4800:
                success = 0
                break
        else:
            print('Export completed')
        print(name + '.tif')
        print(outdir + name + '.tif')
        if success == 1:
           # initialise Google Drive
            drive_handler = gdrive()
            print('Downloading files ...')
            print(name)
            drive_handler.download_file(name + '.tif',
                                        outdir + name + '.tif')
            drive_handler.delete_file(name + '.tif')
        else:
            file_exp.cancel()
