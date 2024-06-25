#!/usr/bin/env python3

import datetime as dt
import logging
import math
import os
import warnings

import ee
import numpy as np

logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)


class GEE_extent(object):
    """
    Class to create an interface with GEE for the extraction of arrays.

    Attributes
    ----------
        minlon: minimum longitude in decimal degrees
        minlat: minumum latitude in decimal degress
        maxlon: maximum longitude in decimal degrees
        maxlat: maximum latitude in decimal degrees
    """

    def __init__(self, minlon, minlat, maxlon, maxlat):
        """Return a new GEE extent object."""

        # construct roi
        roi = ee.Geometry.Polygon(
            [
                [minlon, minlat],
                [minlon, maxlat],
                [maxlon, maxlat],
                [maxlon, minlat],
                [minlon, minlat],
            ]
        )

        self.roi = roi

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
        """Function for multi-temporal."""

        def mapMeanSpace(i):
            reducer = ee.Reducer.mean()
            kernel = ee.Kernel.square(radius, units)
            mean = i.reduceNeighborhood(reducer, kernel).rename(bandNamesMean)
            ratio = i.divide(mean).rename(bandNamesRatio)
            return i.addBands(mean).addBands(ratio)

        if opt_timeWindow is None:
            timeWindow = dict(before=-3, after=3, units="month")
        else:
            timeWindow = opt_timeWindow

        bandNames = ee.Image(images.first()).bandNames()
        bandNamesMean = bandNames.map(lambda b: ee.String(b).cat("_mean"))
        bandNamesRatio = bandNames.map(lambda b: ee.String(b).cat("_ratio"))

        # compute spatial average for all images
        meanSpace = images.map(mapMeanSpace)

        # computes a multi-temporal despeckle function for a single image

        def multitemporalDespeckleSingle(image):
            t = image.date()
            fro = t.advance(ee.Number(timeWindow["before"]), timeWindow["units"])
            to = t.advance(ee.Number(timeWindow["after"]), timeWindow["units"])

            meanSpace2 = (
                ee.ImageCollection(meanSpace)
                .select(bandNamesRatio)
                .filterDate(fro, to)
                .filter(
                    ee.Filter.eq(
                        "relativeOrbitNumber_start",
                        image.get("relativeOrbitNumber_start"),
                    )
                )
            )

            b = image.select(bandNamesMean)

            return (
                b.multiply(meanSpace2.sum())
                .divide(meanSpace2.count())
                .rename(bandNames)
            ).set("system:time_start", image.get("system:time_start"))

        return meanSpace.map(multitemporalDespeckleSingle)

    def get_S1(
        self,
        year,
        month,
        day,
        tempfilter=False,
        tempfilter_radius=7,
        applylcmask=False,
        mask_globcover=True,
        dualpol=True,
        trackflt=None,
        maskwinter=False,
        masksnow=True,
        explicit_t_mask=None,
        ascending=False,
        maskLIA=True,
    ):
        """
        Retrieve the S1 image for a given day from GEE and apply specific filters.
        Assigns outputs to respective instance attributes.

        """

        # save orbit direction based on ascending/descending
        if ascending is True:
            self.ORBIT = "ASCENDING"

        else:
            self.ORBIT = "DESCENDING"

        def computeLIA(image):
            # comput the local incidence angle (LIA) based on the srtm and the s1 viewing angle
            # get the srtm
            srtm = ee.Image("USGS/SRTMGL1_003")
            srtm_slope = ee.Terrain.slope(srtm)
            srtm_aspect = ee.Terrain.aspect(srtm)
            # get the S1 incidence angle
            inc = ee.Image(image).select("angle")
            # comput the LIA
            s = srtm_slope.multiply(
                ee.Image.constant(277)
                .subtract(srtm_aspect)
                .multiply(math.pi / 180)
                .cos()
            )
            lia = inc.subtract(
                ee.Image.constant(90).subtract(ee.Image.constant(90).subtract(s))
            ).abs()
            # add band to current image
            return image.addBands(
                lia.select(["angle"], ["lia"]).reproject(srtm.projection())
            )

        def maskterrain(image):
            # mask for terrain, local incidence angle and high and low backscatter
            tmp = ee.Image(image)
            # srtm dem
            if maskLIA is False:
                gee_srtm = ee.Image("USGS/SRTMGL1_003")
                gee_srtm_slope = ee.Terrain.slope(gee_srtm)
                mask = gee_srtm_slope.lt(20)
            else:
                lia = tmp.select("lia")
                mask = lia.gt(20).bitwiseAnd(lia.lt(45))
            mask2 = tmp.lt(0).bitwiseAnd(tmp.gt(-25))
            mask = mask.bitwiseAnd(mask2)
            tmp = tmp.updateMask(mask)

            return tmp

        def masklc(image):
            # load land cover info
            corine = ee.Image("users/felixgreifeneder/corine")

            # create lc mask
            valLClist = [10, 11, 12, 13, 18, 19, 20, 21, 26, 27, 28, 29]

            lcmask = (
                corine.eq(valLClist[0])
                .bitwiseOr(corine.eq(valLClist[1]))
                .bitwiseOr(corine.eq(valLClist[2]))
                .bitwiseOr(corine.eq(valLClist[3]))
                .bitwiseOr(corine.eq(valLClist[4]))
                .bitwiseOr(corine.eq(valLClist[5]))
                .bitwiseOr(corine.eq(valLClist[6]))
                .bitwiseOr(corine.eq(valLClist[7]))
                .bitwiseOr(corine.eq(valLClist[8]))
                .bitwiseOr(corine.eq(valLClist[9]))
                .bitwiseOr(corine.eq(valLClist[10]))
                .bitwiseOr(corine.eq(valLClist[11]))
            )

            tmp = ee.Image(image)

            tmp = tmp.updateMask(lcmask)
            return tmp

        def mask_lc_globcover(image):
            tmp = ee.Image(image)

            # load lc
            glbcvr = ee.Image("ESA/GLOBCOVER_L4_200901_200912_V2_3").select("landcover")

            valLClist = [
                11,
                14,
                20,
                30,
                40,
                50,
                60,
                70,
                90,
                100,
                110,
                120,
                130,
                140,
                150,
                160,
                170,
                180,
                190,
                200,
                210,
                220,
                230,
            ]

            lcmask = (
                glbcvr.eq(valLClist[0])
                .bitwiseOr(glbcvr.eq(valLClist[1]))
                .bitwiseOr(glbcvr.eq(valLClist[2]))
                .bitwiseOr(glbcvr.eq(valLClist[3]))
                .bitwiseOr(glbcvr.eq(valLClist[4]))
                .bitwiseOr(glbcvr.eq(valLClist[5]))
                .bitwiseOr(glbcvr.eq(valLClist[6]))
                .bitwiseOr(glbcvr.eq(valLClist[7]))
                .bitwiseOr(glbcvr.eq(valLClist[8]))
                .bitwiseOr(glbcvr.eq(valLClist[9]))
                .bitwiseOr(glbcvr.eq(valLClist[10]))
                .bitwiseOr(glbcvr.eq(valLClist[11]))
                .bitwiseOr(glbcvr.eq(valLClist[12]))
                .bitwiseOr(glbcvr.eq(valLClist[13]))
                .bitwiseOr(glbcvr.eq(valLClist[14]))
                .bitwiseOr(glbcvr.eq(valLClist[15]))
                .bitwiseOr(glbcvr.eq(valLClist[16]))
                .bitwiseOr(glbcvr.eq(valLClist[17]))
                .bitwiseOr(glbcvr.eq(valLClist[18]))
                .bitwiseOr(glbcvr.eq(valLClist[19]))
                .bitwiseOr(glbcvr.eq(valLClist[20]))
                .bitwiseOr(glbcvr.eq(valLClist[21]))
                .bitwiseOr(glbcvr.eq(valLClist[22]))
            )

            tmp = tmp.updateMask(lcmask)

            return tmp

        def setresample(image):
            image = image.resample()
            return image

        def toln(image):
            tmp = ee.Image(image)

            # Convert to linear
            vv = ee.Image(10).pow(tmp.select("VV").divide(10))
            if dualpol is True:
                vh = ee.Image(10).pow(tmp.select("VH").divide(10))

            # Convert to ln
            out = vv.log()
            if dualpol is True:
                out = out.addBands(vh.log())
                out = out.select(["constant", "constant_1"], ["VV", "VH"])
            else:
                out = out.select(["constant"], ["VV"])

            return out.set("system:time_start", tmp.get("system:time_start"))

        def tolin(image):
            tmp = ee.Image(image)

            # Covert to linear
            vv = ee.Image(10).pow(tmp.select("VV").divide(10))
            if dualpol is True:
                vh = ee.Image(10).pow(tmp.select("VH").divide(10))

            # Convert to
            if dualpol is True:
                out = vv.addBands(vh)
                out = out.select(["constant", "constant_1"], ["VV", "VH"])
            else:
                out = vv.select(["constant"], ["VV"])

            return out.set("system:time_start", tmp.get("system:time_start"))

        def todb(image):
            tmp = ee.Image(image)

            return (
                ee.Image(10)
                .multiply(tmp.log10())
                .set("system:time_start", tmp.get("system:time_start"))
            )

        def applysnowmask(image):
            tmp = ee.Image(image)
            sdiff = tmp.select("VH").subtract(snowref)
            wetsnowmap = sdiff.lte(-2.6).focal_mode(100, "square", "meters", 3)

            return tmp.updateMask(wetsnowmap.eq(0))

        def projectlia(image):
            tmp = ee.Image(image)
            trgtprj = tmp.select("VV").projection()
            tmp = tmp.addBands(tmp.select("angle").reproject(trgtprj), ["angle"], True)
            return tmp

        def apply_explicit_t_mask(image):
            t_mask = ee.Image("users/felixgreifeneder/" + explicit_t_mask)
            mask = t_mask.eq(0)
            return image.updateMask(mask)


        # load S1 data
        gee_s1_collection = ee.ImageCollection("COPERNICUS/S1_GRD")

        # Filter the image collection
        gee_s1_filtered = (
            gee_s1_collection.filter(ee.Filter.eq("instrumentMode", "IW"))
            .filterBounds(self.roi)
            .filter(ee.Filter.eq("platform_number", "A"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        )

        if ascending is True:
            gee_s1_filtered = gee_s1_filtered.filter(
                ee.Filter.eq("orbitProperties_pass", "ASCENDING")
            )
        else:
            gee_s1_filtered = gee_s1_filtered.filter(
                ee.Filter.eq("orbitProperties_pass", "DESCENDING")
            )

        if dualpol is True:
            # Consider only dual-pol scenes
            gee_s1_filtered = gee_s1_filtered.filter(
                ee.Filter.listContains("transmitterReceiverPolarisation", "VH")
            )

        if trackflt is not None:
            # Specify track
            gee_s1_filtered = gee_s1_filtered.filter(
                ee.Filter.eq("relativeOrbitNumber_start", trackflt)
            )

        if maskwinter is True:
            # Mask winter based on DOY
            gee_s1_filtered = gee_s1_filtered.filter(ee.Filter.dayOfYear(121, 304))

        # add LIA
        if maskLIA is True:
            # compute the local incidence angle if it shall be used for masking
            gee_s1_filtered = gee_s1_filtered.map(computeLIA)
            s1_lia = gee_s1_filtered.select("lia")
        else:
            s1_lia = None

        s1_angle = gee_s1_filtered.select("angle")

        if applylcmask is True:
            # apply land-cover mask based on Corine
            gee_s1_filtered = gee_s1_filtered.map(masklc)
        if mask_globcover is True:
            # apply land-cover mask based on globcover
            gee_s1_filtered = gee_s1_filtered.map(mask_lc_globcover)

        # Enable bilinear resampling (instead of NN)
        gee_s1_filtered = gee_s1_filtered.map(setresample)

        if explicit_t_mask is None:
            # apply masking based on the terraing (LIA)
            gee_s1_filtered = gee_s1_filtered.map(maskterrain)
        else:
            # apply specific terrain mask
            gee_s1_filtered = gee_s1_filtered.map(apply_explicit_t_mask)

        if masksnow is True:
            # automatic wet snow masking
            gee_s1_linear_vh = gee_s1_filtered.map(tolin).select("VH")
            snowref = ee.Image(10).multiply(
                gee_s1_linear_vh.reduce(ee.Reducer.intervalMean(5, 100)).log10()
            )
            gee_s1_filtered = gee_s1_filtered.map(applysnowmask)

        #### SHOULD BE IF STATEMENT HERE

        # create a list of availalbel dates
        try:
            tmp = gee_s1_filtered.getInfo()

        except Exception as e:
            # If EEException: Collection query aborted after accumulating over 5000 elements.
            # raise an error and suggest to use a smaller area of interest
            if "5000" in str(e):
                raise Exception(
                    "There are too many S1 images with the selected filters, please consider "
                    "reducing the area of interest."
                )
            else:
                raise e

        tmp_ids = [x["properties"]["system:index"] for x in tmp["features"]]

        dates = np.array(
            [
                dt.date(year=int(x[17:21]), month=int(x[21:23]), day=int(x[23:25]))
                for x in tmp_ids
            ]
        )

        if not len(dates):
            raise Exception(
                "There are no S1 images with the selected filters, please consider "
                "changing the area of interest or selecting a different orbit"
            )

        # find the closest acquisitions
        doi = dt.date(year=year, month=month, day=day)
        doi_index = np.argmin(np.abs(dates - doi))
        date_selected = dates[doi_index]

        # filter imagecollection for respective date
        gee_s1_drange = gee_s1_filtered.filterDate(
            date_selected.strftime("%Y-%m-%d"),
            (date_selected + dt.timedelta(days=1)).strftime("%Y-%m-%d"),
        )
        s1_angle_drange = s1_angle.filterDate(
            date_selected.strftime("%Y-%m-%d"),
            (date_selected + dt.timedelta(days=1)).strftime("%Y-%m-%d"),
        )
        if maskLIA is True:
            s1_lia_drange = s1_lia.filterDate(
                date_selected.strftime("%Y-%m-%d"),
                (date_selected + dt.timedelta(days=1)).strftime("%Y-%m-%d"),
            )
        if gee_s1_drange.size().getInfo() > 1:
            if maskLIA is True:
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
        track_nr = s1_sig0_info["properties"]["relativeOrbitNumber_start"]

        # only uses images of the same track
        gee_s1_filtered = gee_s1_filtered.filterMetadata(
            "relativeOrbitNumber_start", "equals", track_nr
        )

        if tempfilter is True:
            # despeckle
            radius = tempfilter_radius
            units = "pixels"
            gee_s1_linear = gee_s1_filtered.map(tolin)
            gee_s1_dspckld_vv = self._multitemporalDespeckle(
                gee_s1_linear.select("VV"),
                radius,
                units,
                {"before": -12, "after": 12, "units": "month"},
            )
            gee_s1_dspckld_vv = gee_s1_dspckld_vv.map(todb)
            gee_s1_fltrd_vv = gee_s1_dspckld_vv.filterDate(
                date_selected.strftime("%Y-%m-%d"),
                (date_selected + dt.timedelta(days=1)).strftime("%Y-%m-%d"),
            )
            s1_sig0_vv = gee_s1_fltrd_vv.mosaic()

            if dualpol is True:
                gee_s1_dspckld_vh = self._multitemporalDespeckle(
                    gee_s1_linear.select("VH"),
                    radius,
                    units,
                    {"before": -12, "after": 12, "units": "month"},
                )
                gee_s1_dspckld_vh = gee_s1_dspckld_vh.map(todb)
                gee_s1_fltrd_vh = gee_s1_dspckld_vh.filterDate(
                    date_selected.strftime("%Y-%m-%d"),
                    (date_selected + dt.timedelta(days=1)).strftime("%Y-%m-%d"),
                )
                s1_sig0_vh = gee_s1_fltrd_vh.mosaic()

            if dualpol is True:
                s1_sig0 = s1_sig0_vv.addBands(s1_sig0_vh).select(
                    ["constant", "constant_1"], ["VV", "VH"]
                )
            else:
                s1_sig0 = s1_sig0_vv.select(["constant"], ["VV"])

        # extract information
        s1_sig0_vv = s1_sig0.select("VV")
        s1_sig0_vv = s1_sig0_vv.clip(self.roi)
        if dualpol is True:
            s1_sig0_vh = s1_sig0.select("VH")
            s1_sig0_vh = s1_sig0_vh.clip(self.roi)

        gee_s1_ln = gee_s1_filtered.map(toln)
        gee_s1_lin = gee_s1_filtered.map(tolin)
        k1vv = ee.Image(gee_s1_ln.select("VV").mean()).clip(self.roi)
        k2vv = ee.Image(gee_s1_ln.select("VV").reduce(ee.Reducer.stdDev())).clip(
            self.roi
        )
        mean_vv = ee.Image(gee_s1_lin.select("VV").mean()).clip(self.roi)
        std_vv = ee.Image(gee_s1_lin.select("VV").reduce(ee.Reducer.stdDev())).clip(
            self.roi
        )

        if dualpol is True:
            k1vh = ee.Image(gee_s1_ln.select("VH").mean()).clip(self.roi)
            k2vh = ee.Image(gee_s1_ln.select("VH").reduce(ee.Reducer.stdDev())).clip(
                self.roi
            )
            mean_vh = ee.Image(gee_s1_lin.select("VH").mean()).clip(self.roi)
            std_vh = ee.Image(gee_s1_lin.select("VH").reduce(ee.Reducer.stdDev())).clip(
                self.roi
            )

        # export
        if dualpol is False:
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

        if maskLIA is True:
            self.S1_LIA = s1_lia

    def estimate_SM(self):
        # load SVR model

        warnings.simplefilter(
            action="ignore", category=FutureWarning
        )  # Hide the warnings
        warnings.simplefilter(action="ignore", category=UserWarning)

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
        new_model_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "model_dict.npy"
        )
        model_param = np.load(new_model_path, allow_pickle=True).item()

        # recunstruct the parameters used in classification
        # alpha1 = [ee.Image(MLmodel1['SVRmodel'].best_estimator_.dual_coef_[0][i]) for i in
        #         range(len(MLmodel1['SVRmodel'].best_estimator_.dual_coef_[0]))]
        alpha1 = [
            ee.Image(model_param["model1"]["alpha_array"][i])
            for i in range(len(model_param["model1"]["alpha_array"]))
        ]
        gamma1 = ee.Image(-model_param["model1"]["gamma"])
        intercept1 = ee.Image(model_param["model1"]["intercept"])
        sup_vectors1 = model_param["model1"]["support_vectors"]
        # --------------------------------------------------------------------

        # support vectors stack
        # sup_vectors1 = MLmodel1['SVRmodel'].best_estimator_.support_vectors_
        n_vectors1 = sup_vectors1.shape[0]
        n_features1 = 8

        tmp_list = [ee.Image(sup_vectors1[0, i]) for i in range(n_features1)]

        sup_image1 = ee.Image.cat(tmp_list).select(
            [
                "constant",
                "constant_1",
                "constant_2",
                "constant_3",
                "constant_4",
                "constant_5",
                "constant_6",
                "constant_7",
            ],
            ["VVk1", "VHk1", "VVk2", "VHk2", "lc", "lia", "aspect", "gldas_mean"],
        )
        sup_list1 = [sup_image1]

        for i in range(1, n_vectors1):
            tmp_list = [ee.Image(sup_vectors1[i, j]) for j in range(n_features1)]

            sup_image1 = ee.Image.cat(tmp_list).select(
                [
                    "constant",
                    "constant_1",
                    "constant_2",
                    "constant_3",
                    "constant_4",
                    "constant_5",
                    "constant_6",
                    "constant_7",
                ],
                ["VVk1", "VHk1", "VVk2", "VHk2", "lc", "lia", "aspect", "gldas_mean"],
            )
            sup_list1.append(sup_image1)

        # create estimation stack
        vv = self.S1_SIG0_VV_db
        k1_vv = self.K1VV
        k1_vh = self.K1VH
        k2_vv = self.K2VV
        k2_vh = self.K2VH
        lia = self.S1_ANGLE.rename(["lia"])
        aspect = self.TERRAIN[2].rename(["aspect"])
        self.TERRAIN[1].rename(["slope"])
        self.TERRAIN[0].rename(["height"])
        gldas_img = self.GLDAS_IMG
        gldas_mean = self.GLDAS_MEAN
        lc = self.LAND_COVER

        input_image1 = ee.Image(
            [
                k1_vv.toFloat(),
                k1_vh.toFloat(),
                k2_vv.toFloat(),
                k2_vh.toFloat(),
                lc.toFloat(),
                lia.toFloat(),
                aspect.toFloat(),
                gldas_mean.toFloat(),
            ]
        )
        ipt_img_mask1 = input_image1.mask().reduce(ee.Reducer.allNonZero())
        S1mask = vv.mask()
        zeromask = input_image1.neq(ee.Image(0)).reduce(ee.Reducer.allNonZero())
        combined_mask = S1mask.And(zeromask).And(ipt_img_mask1)

        input_image1 = input_image1.updateMask(ee.Image(combined_mask))

        # scale the estimation image
        # replace
        # scaling_std_img1 = ee.Image(
        #    [ee.Image(MLmodel1['scaler'].scale_[i].astype(np.float)) for i in range(n_features1)])
        scaling_std_img1 = ee.Image(
            [
                ee.Image(model_param["model1"]["scaler_scale"][i].astype(float))
                for i in range(n_features1)
            ]
        )

        scaling_std_img1 = scaling_std_img1.select(
            [
                "constant",
                "constant_1",
                "constant_2",
                "constant_3",
                "constant_4",
                "constant_5",
                "constant_6",
                "constant_7",
            ],
            ["VVk1", "VHk1", "VVk2", "VHk2", "lc", "lia", "aspect", "gldas_mean"],
        )

        # scaling_mean_img1 = ee.Image(
        #    [ee.Image(MLmodel1['scaler'].center_[i].astype(np.float)) for i in range(n_features1)])
        ### REPLACEMENT ###
        scaling_mean_img1 = ee.Image(
            [
                ee.Image(model_param["model1"]["scaler_center"][i].astype(float))
                for i in range(n_features1)
            ]
        )

        scaling_mean_img1 = scaling_mean_img1.select(
            [
                "constant",
                "constant_1",
                "constant_2",
                "constant_3",
                "constant_4",
                "constant_5",
                "constant_6",
                "constant_7",
            ],
            ["VVk1", "VHk1", "VVk2", "VHk2", "lc", "lia", "aspect", "gldas_mean"],
        )

        input_image_scaled1 = input_image1.subtract(scaling_mean_img1).divide(
            scaling_std_img1
        )

        k_x1x2_1 = [
            sup_list1[i]
            .subtract(input_image_scaled1)
            .pow(ee.Image(2))
            .reduce(ee.Reducer.sum())
            .sqrt()
            .pow(ee.Image(2))
            .multiply(ee.Image(gamma1))
            .exp()
            for i in range(n_vectors1)
        ]

        alpha_times_k1 = [
            ee.Image(alpha1[i].multiply(k_x1x2_1[i])) for i in range(n_vectors1)
        ]

        # print(n_vectors1)

        alpha_times_k_sum_1 = ee.ImageCollection(alpha_times_k1).reduce(
            ee.Reducer.sum()
        )
        # alpha_times_k_sum = alpha_times_k.reduce(ee.Reducer.sum())

        # print(alpha_times_k_sum.getInfo())

        estimated_smc_average = alpha_times_k_sum_1.add(intercept1)

        # estimate relative smc

        # create parameter images
        # alpha2 = [ee.Image(MLmodel2['SVRmodel'].best_estimator_.dual_coef_[0][i]) for i in
        #          range(len(MLmodel2['SVRmodel'].best_estimator_.dual_coef_[0]))]
        # gamma2 = ee.Image(-MLmodel2['SVRmodel'].best_estimator_.gamma)
        # intercept2 = ee.Image(MLmodel2['SVRmodel'].best_estimator_.intercept_[0])

        ### REPLACEMENT####
        alpha2 = [
            ee.Image(model_param["model2"]["alpha_array"][i])
            for i in range(len(model_param["model2"]["alpha_array"]))
        ]
        gamma2 = ee.Image(-model_param["model2"]["gamma"])
        intercept2 = ee.Image(model_param["model2"]["intercept"])
        sup_vectors2 = model_param["model2"]["support_vectors"]

        # support vectors stack
        # sup_vectors2 = MLmodel2['SVRmodel'].best_estimator_.support_vectors_
        n_vectors2 = sup_vectors2.shape[0]
        n_features2 = 3

        tmp_list = [ee.Image(sup_vectors2[0, i]) for i in range(n_features2)]

        sup_image2 = ee.Image.cat(tmp_list).select(
            ["constant", "constant_1", "constant_2"], ["relVV", "relVH", "gldas"]
        )
        sup_list2 = [sup_image2]

        for i in range(1, n_vectors2):
            tmp_list = [ee.Image(sup_vectors2[i, j]) for j in range(n_features2)]

            sup_image2 = ee.Image.cat(tmp_list).select(
                ["constant", "constant_1", "constant_2"], ["relVV", "relVH", "gldas"]
            )
            sup_list2.append(sup_image2)

        # create estimation stack
        vv = self.S1_SIG0_VV_db
        vh = self.S1_SIG0_VH_db
        vv_mean = self.S1MEAN_VV
        vh_mean = self.S1MEAN_VH

        vv_lin = ee.Image(10).pow(vv.divide(10)).rename(["relVV"])
        vh_lin = ee.Image(10).pow(vh.divide(10)).rename(["relVH"])

        input_image2 = ee.Image(
            [
                vv_lin.subtract(vv_mean).toFloat(),
                vh_lin.subtract(vh_mean).toFloat(),
                gldas_img.subtract(gldas_mean).rename(["gldas"]).toFloat(),
            ]
        )
        ipt_img_mask2 = input_image2.mask().reduce(ee.Reducer.allNonZero())
        S1mask = vv.mask()
        zeromask = input_image2.neq(ee.Image(0)).reduce(ee.Reducer.allNonZero())
        combined_mask = S1mask.And(zeromask).And(ipt_img_mask2)

        input_image2 = input_image2.updateMask(ee.Image(combined_mask))

        # scale the estimation image
        scaling_std_img2 = ee.Image(
            [
                ee.Image(model_param["model2"]["scaler_scale"][i].astype(float))
                for i in range(n_features2)
            ]
        )

        scaling_std_img2 = scaling_std_img2.select(
            ["constant", "constant_1", "constant_2"], ["relVV", "relVH", "gldas"]
        )

        scaling_mean_img2 = ee.Image(
            [
                ee.Image(model_param["model2"]["scaler_center"][i].astype(float))
                for i in range(n_features2)
            ]
        )

        scaling_mean_img2 = scaling_mean_img2.select(
            ["constant", "constant_1", "constant_2"], ["relVV", "relVH", "gldas"]
        )

        input_image_scaled2 = input_image2.subtract(scaling_mean_img2).divide(
            scaling_std_img2
        )

        k_x1x2_2 = [
            sup_list2[i]
            .subtract(input_image_scaled2)
            .pow(ee.Image(2))
            .reduce(ee.Reducer.sum())
            .sqrt()
            .pow(ee.Image(2))
            .multiply(ee.Image(gamma2))
            .exp()
            for i in range(n_vectors2)
        ]

        alpha_times_k2 = [
            ee.Image(alpha2[i].multiply(k_x1x2_2[i])) for i in range(n_vectors2)
        ]

        # print(n_vectors2)

        alpha_times_k_sum_2 = ee.ImageCollection(alpha_times_k2).reduce(
            ee.Reducer.sum()
        )

        estimated_smc_relative = alpha_times_k_sum_2.add(intercept2)

        estimated_smc = (
            estimated_smc_average.add(estimated_smc_relative)
            .multiply(100)
            .round()
            .int8()
        )

        # mask negative values
        estimated_smc = estimated_smc.updateMask(estimated_smc.gt(0))
        self.ESTIMATED_SM = estimated_smc

    def get_S1_dates(self, tracknr=None, dualpol=True, ascending=True):
        # load S1 data
        gee_s1_collection = ee.ImageCollection("COPERNICUS/S1_GRD")

        gee_s1_filtered = (
            gee_s1_collection.filter(ee.Filter.eq("instrumentMode", "IW"))
            .filterBounds(self.roi)
            .filter(ee.Filter.eq("platform_number", "A"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        )

        if ascending is True:
            gee_s1_filtered = gee_s1_filtered.filter(
                ee.Filter.eq("orbitProperties_pass", "ASCENDING")
            )
        else:
            gee_s1_filtered = gee_s1_filtered.filter(
                ee.Filter.eq("orbitProperties_pass", "DESCENDING")
            )

        if dualpol is True:
            gee_s1_filtered = gee_s1_filtered.filter(
                ee.Filter.listContains("transmitterReceiverPolarisation", "VH")
            )

        if tracknr is not None:
            gee_s1_filtered = gee_s1_filtered.filter(
                ee.Filter.eq("relativeOrbitNumber_start", tracknr)
            )

        # create a list of availalbel dates
        try:
            tmp = gee_s1_filtered.getInfo()

        except Exception as e:
            # If EEException: Collection query aborted after accumulating over 5000 elements.
            # raise an error and suggest to use a smaller area of interest
            if "5000" in str(e):
                raise Exception(
                    "There are too many S1 images with the selected filters, please consider "
                    "reducing the area of interest."
                )
            else:
                raise e

        tmp_ids = [x["properties"]["system:index"] for x in tmp["features"]]
        dates = np.array(
            [
                dt.date(year=int(x[17:21]), month=int(x[21:23]), day=int(x[23:25]))
                for x in tmp_ids
            ]
        )

        if not len(dates):
            raise Exception(
                "There are no S1 images with the selected filters, please consider "
                "changing the area of interest or selecting a different orbit"
            )

        return dates

    def get_gldas(self, date=None):
        # get GLDAS, date can be passed as a string or copied from the extracted S1 scene
        if date is None:
            doi = ee.Date(self.S1_DATE.strftime(format="%Y-%m-%d"))

        gldas_mean = (
            ee.ImageCollection("NASA/GLDAS/V021/NOAH/G025/T3H")
            .select("SoilMoi0_10cm_inst")
            .filterDate("2014-10-01", "2018-01-22")
            .reduce(ee.Reducer.mean())
        )

        gldas_mean = ee.Image(gldas_mean).resample().clip(self.roi)

        gldas = (
            ee.ImageCollection("NASA/GLDAS/V021/NOAH/G025/T3H")
            .select("SoilMoi0_10cm_inst")
            .filterDate(doi, doi.advance(3, "hour"))
        )

        if gldas.size().getInfo() == 0:
            # print('No GLDAS product for specified date')
            gldas_test = ee.ImageCollection("NASA/GLDAS/V021/NOAH/G025/T3H").select(
                "SoilMoi0_10cm_inst"
            )
            gldas_test.aggregate_max("system:index").getInfo()
            # print(('ID of latest available product: ' + last_gldas))
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
        land_cover = globcover_image.select("landcover").clip(self.roi)
        self.LAND_COVER = land_cover

    def get_terrain(self):
        # get SRTM data
        elev = ee.Image("CGIAR/SRTM90_V4").select("elevation").clip(self.roi)
        aspe = (
            ee.Terrain.aspect(ee.Image("CGIAR/SRTM90_V4"))
            .select("aspect")
            .clip(self.roi)
        )
        slop = (
            ee.Terrain.slope(ee.Image("CGIAR/SRTM90_V4")).select("slope").clip(self.roi)
        )

        self.TERRAIN = (elev, aspe, slop)
