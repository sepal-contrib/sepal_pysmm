"""This is a forked version of the code produced in https://github.com/sepal-contrib/sepal_pysmm
It has some modifications to make it work such as:

- change MOD13Q1.061 Terra Vegetation Indices 16-Day Global 250m from "MODIS/001/MOD13Q1" to "MODIS/061/MOD13Q1"
- remove QA filtering from MODIS/061/MOD13Q1 due to too many missing values

"""

import ee
import numpy as np
import datetime as dt
import math


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
        self.MINLON = minlon
        self.MINLAT = minlat
        self.sampling = sampling
        self.workdir = workdir

        # Placeholders
        self.S1_SIG0_VV_db = None
        self.S1_G0VOL_VV_db = None
        self.S1_G0SURF_VV_db = None
        self.S1_ANGLE = None
        self.S1_LIA = None
        self.K1VV = None
        self.K2VV = None
        self.K3VV = None
        self.K4VV = None
        self.K1G0VV_V = None
        self.K2G0VV_V = None
        self.K3G0VV_V = None
        self.K4G0VV_V = None
        self.K1G0VV_S = None
        self.K2G0VV_S = None
        self.K3G0VV_S = None
        self.K4G0VV_S = None
        self.S1MEAN_VV = None
        self.S1STD_VV = None
        self.S1G0VOLMEAN_VV = None
        self.S1G0VOLSTD_VV = None
        self.S1G0SURFMEAN_VV = None
        self.S1G0SURFSTD_VV = None
        self.S1_DATE = None
        self.S1_SIG0_VH_db = None
        self.S1_G0VOL_VH_db = None
        self.S1_G0SURF_VH_db = None
        self.K1VH = None
        self.K2VH = None
        self.K3VH = None
        self.K4VH = None
        self.K1G0VH_V = None
        self.K2G0VH_V = None
        self.K3G0VH_V = None
        self.K4G0VH_V = None
        self.K1G0VH_S = None
        self.K2G0VH_S = None
        self.K3G0VH_S = None
        self.K4G0VH_S = None
        self.S1MEAN_VH = None
        self.S1STD_VH = None
        self.S1G0VOLMEAN_VH = None
        self.S1G0VOLSTD_VH = None
        self.S1G0SURFMEAN_VH = None
        self.S1G0SURFSTD_VH = None
        self.ESTIMATED_SM = None
        self.GLDAS_IMG = None
        self.GLDAS_MEAN = None
        self.LAND_COVER = None
        self.TERRAIN = None
        self.L8_IMG = None
        self.L8_MEAN = None
        self.L8_MASK = None
        self.TREE_COVER = None
        self.LAST_GLDAS = dt.datetime.today()  # temporary
        self.LC_ID = None
        self.FOREST_TYPE = None
        self.BARE_COVER = None
        self.CROPS_COVER = None
        self.GRASS_COVER = None
        self.MOSS_COVER = None
        self.SHRUB_COVER = None
        self.TREE_COVER = None
        self.URBAN_COVER = None
        self.WATERP_COVER = None
        self.WATERS_COVER = None
        self.SAND = None
        self.CLAY = None
        self.BULK = None
        self.EVI_IMG = None
        self.EVI_MEAN = None
        self.OVERWRITE = None

    def _multitemporalDespeckle(self, images, radius, units, opt_timeWindow=None):
        """Function for multi-temporal despeckling"""

        def mapMeanSpace(i):
            reducer = ee.Reducer.mean()
            kernel = ee.Kernel.square(radius, units)
            mean = i.reduceNeighborhood(reducer, kernel).rename(bandNamesMean)
            ratio = i.divide(mean).rename(bandNamesRatio)
            return i.addBands(mean).addBands(ratio)

        if opt_timeWindow == None:
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

    def _slope_correction(self, collection, elevation, model, buffer=0):
        """This function applies the slope correction on a collection of Sentinel-1 data

        :param collection: ee.Collection of Sentinel-1
        :param elevation: ee.Image of DEM
        :param model: model to be applied (volume/surface)
        :param buffer: buffer in meters for layover/shadow amsk

         :returns: ee.Image
        """

        def _volumetric_model_SCF(theta_iRad, alpha_rRad):
            """Code for calculation of volumetric model SCF

            :param theta_iRad: ee.Image of incidence angle in radians
            :param alpha_rRad: ee.Image of slope steepness in range

            :returns: ee.Image
            """

            # create a 90 degree image in radians
            ninetyRad = ee.Image.constant(90).multiply(np.pi / 180)

            # model
            nominator = (ninetyRad.subtract(theta_iRad).add(alpha_rRad)).tan()
            denominator = (ninetyRad.subtract(theta_iRad)).tan()
            return nominator.divide(denominator)

        def _surface_model_SCF(theta_iRad, alpha_rRad, alpha_azRad):
            """Code for calculation of direct model SCF

            :param theta_iRad: ee.Image of incidence angle in radians
            :param alpha_rRad: ee.Image of slope steepness in range
            :param alpha_azRad: ee.Image of slope steepness in azimuth

            :returns: ee.Image
            """

            # create a 90 degree image in radians
            ninetyRad = ee.Image.constant(90).multiply(np.pi / 180)

            # model
            nominator = (ninetyRad.subtract(theta_iRad)).cos()
            denominator = alpha_azRad.cos().multiply(
                (ninetyRad.subtract(theta_iRad).add(alpha_rRad)).cos()
            )

            return nominator.divide(denominator)

        def _erode(image, distance):
            """Buffer function for raster

            :param image: ee.Image that shoudl be buffered
            :param distance: distance of buffer in meters

            :returns: ee.Image
            """

            d = (
                image.Not()
                .unmask(1)
                .fastDistanceTransform(30)
                .sqrt()
                .multiply(ee.Image.pixelArea().sqrt())
            )

            return image.updateMask(d.gt(distance))

        def _masking(alpha_rRad, theta_iRad, buffer):
            """Masking of layover and shadow


            :param alpha_rRad: ee.Image of slope steepness in range
            :param theta_iRad: ee.Image of incidence angle in radians
            :param buffer: buffer in meters

            :returns: ee.Image
            """
            # layover, where slope > radar viewing angle
            layover = alpha_rRad.lt(theta_iRad).rename("layover")

            # shadow
            ninetyRad = ee.Image.constant(90).multiply(np.pi / 180)
            shadow = alpha_rRad.gt(
                ee.Image.constant(-1).multiply(ninetyRad.subtract(theta_iRad))
            ).rename("shadow")

            # add buffer to layover and shadow
            if buffer > 0:
                layover = _erode(layover, buffer)
                shadow = _erode(shadow, buffer)

                # combine layover and shadow
            no_data_mask = layover.And(shadow).rename("no_data_mask")

            return layover.addBands(shadow).addBands(no_data_mask)

        def _correct(image):
            """This function applies the slope correction and adds layover and shadow masks"""

            # get the image geometry and projection
            geom = image.geometry()
            proj = image.select(1).projection()

            # calculate the look direction
            heading = (
                ee.Terrain.aspect(image.select("angle"))
                .reduceRegion(ee.Reducer.mean(), geom, 1000, tileScale=4)
                .get("aspect")
            )

            # Sigma0 to Power of input image
            sigma0Pow = ee.Image.constant(10).pow(image.divide(10.0))

            # the numbering follows the article chapters
            # 2.1.1 Radar geometry
            theta_iRad = image.select("angle").multiply(np.pi / 180)
            phi_iRad = ee.Image.constant(heading).multiply(np.pi / 180)

            # 2.1.2 Terrain geometry
            alpha_sRad = (
                ee.Terrain.slope(elevation)
                .select("slope")
                .multiply(np.pi / 180)
                .setDefaultProjection(proj)
                .clip(geom)
            )
            phi_sRad = (
                ee.Terrain.aspect(elevation)
                .select("aspect")
                .multiply(np.pi / 180)
                .setDefaultProjection(proj)
                .clip(geom)
            )

            # we get the height, for export
            height = elevation.setDefaultProjection(proj).clip(geom)

            # 2.1.3 Model geometry
            # reduce to 3 angle
            phi_rRad = phi_iRad.subtract(phi_sRad)

            # slope steepness in range (eq. 2)
            alpha_rRad = (alpha_sRad.tan().multiply(phi_rRad.cos())).atan()

            # slope steepness in azimuth (eq 3)
            alpha_azRad = (alpha_sRad.tan().multiply(phi_rRad.sin())).atan()

            # local incidence angle (eq. 4)
            theta_liaRad = (
                alpha_azRad.cos().multiply((theta_iRad.subtract(alpha_rRad)).cos())
            ).acos()
            theta_liaDeg = theta_liaRad.multiply(180 / np.pi)

            # 2.2
            # Gamma_nought
            gamma0 = sigma0Pow.divide(theta_iRad.cos())
            gamma0dB = (
                ee.Image.constant(10)
                .multiply(gamma0.log10())
                .select(["VV", "VH"], ["VV_gamma0", "VH_gamma0"])
            )
            ratio_gamma = (
                gamma0dB.select("VV_gamma0")
                .subtract(gamma0dB.select("VH_gamma0"))
                .rename("ratio_gamma0")
            )

            if model == "volume":
                scf = _volumetric_model_SCF(theta_iRad, alpha_rRad)

            if model == "surface":
                scf = _surface_model_SCF(theta_iRad, alpha_rRad, alpha_azRad)

            # apply model for Gamm0_f
            gamma0_flat = gamma0.divide(scf)
            gamma0_flatDB = (
                ee.Image.constant(10)
                .multiply(gamma0_flat.log10())
                .select(["VV", "VH"], ["VV_gamma0flat", "VH_gamma0flat"])
            )

            masks = _masking(alpha_rRad, theta_iRad, buffer)

            # calculate the ratio for RGB vis
            ratio_flat = (
                gamma0_flatDB.select("VV_gamma0flat")
                .subtract(gamma0_flatDB.select("VH_gamma0flat"))
                .rename("ratio_gamma0flat")
            )

            if model == "surface":
                gamma0_flatDB = gamma0_flatDB.rename(["VV_gamma0surf", "VH_gamma0surf"])

            if model == "volume":
                gamma0_flatDB = gamma0_flatDB.rename(["VV_gamma0vol", "VH_gamma0vol"])

            return (
                image.rename(["VV_sigma0", "VH_sigma0", "incAngle"])
                .addBands(gamma0dB)
                .addBands(ratio_gamma)
                .addBands(gamma0_flatDB)
                .addBands(ratio_flat)
                .addBands(alpha_rRad.rename("alpha_rRad"))
                .addBands(alpha_azRad.rename("alpha_azRad"))
                .addBands(phi_sRad.rename("aspect"))
                .addBands(alpha_sRad.rename("slope"))
                .addBands(theta_iRad.rename("theta_iRad"))
                .addBands(theta_liaRad.rename("theta_liaRad"))
                .addBands(masks)
                .addBands(height.rename("elevation"))
            )

            # run and return correction

        return collection.map(_correct, opt_dropNulls=True)

    def init_SM_retrieval(
        self, year, month, day, hour=12, minute=0, track=None, overwrite=False
    ):
        # initiate all datasets for the retrieval of soil moisture
        self.get_copernicus_lc()

        self.get_S1_tmp_collection(
            year,
            month,
            day,
            hour,
            minute,
            mask_copernicuslc=True,
            trackflt=track,
            ascending=False,
        )
        self.match_evi()

        self.match_l8()
        # self.match_gldas()

        self.get_l8()

        self.get_modis_evi()

        self.get_S1(tempfilter=False, mask_snow_frozen_GLDAS=False)

        self.get_sand_content()
        self.get_clay_content()
        self.get_bulk_density()

        self.OVERWRITE = overwrite

    def get_S1(
        self, tempfilter=False, tempfilter_radius=7, mask_snow_frozen_GLDAS=False
    ):
        """Retrieve the S1 image for a given day from GEE and apply specific filters.
        Assigns outputs to respective instance attributes

        """

        def tolin(image):
            tmp = ee.Image(image)

            # Covert to linear
            out = ee.Image(10).pow(
                tmp.select(
                    ["VV_gamma0vol", "VH_gamma0vol", "VV_gamma0surf", "VH_gamma0surf"]
                ).divide(10)
            )
            # rename
            # out = out.select(['constant_0', 'constant_2', 'constant_3'],
            #                 ['VV_gamma0vol', 'VV_gamma0surf', 'VH_gamma0surf'])

            return out.set("system:time_start", tmp.get("system:time_start"))

        def todb(image):
            tmp = ee.Image(image)

            return (
                ee.Image(10)
                .multiply(tmp.log10())
                .set("system:time_start", tmp.get("system:time_start"))
            )

        def create_gldas_snow_frozen_mask(image):
            s1 = ee.Image(image.get("primary"))
            gldas = ee.Image(image.get("secondary"))

            mask = ee.Image(
                gldas.expression(
                    "(b('SWE_inst') < 3) && (b('SoilTMP0_10cm_inst') > 275) ? 1 : 0"
                )
            )

            return s1.updateMask(mask)

        def mask_evi(image):
            s1 = ee.Image(image.get("primary"))
            evi = ee.Image(image.get("secondary"))
            return s1.updateMask(evi.select(0).mask())

        gee_s1_filtered = self.S1_reference_stack

        if mask_snow_frozen_GLDAS:
            # mask snow frozen from GLDAS and ndvi from
            gldas_filt = ee.Filter.equals(
                leftField="system:time_start", rightField="system:time_start"
            )
            innjoin = ee.Join.inner()
            joined_s1_gldas = innjoin.apply(
                gee_s1_filtered, self.GLDAS_STACK, gldas_filt
            )

            gee_s1_filtered = ee.ImageCollection(
                joined_s1_gldas.map(create_gldas_snow_frozen_mask)
            )

        # mask evi
        evi_filt = ee.Filter.equals(
            leftField="system:time_start", rightField="system:time_start"
        )
        innjoin2 = ee.Join.inner()
        joined_s1_evi = innjoin2.apply(gee_s1_filtered, self.EVI_STACK, evi_filt)
        gee_s1_filtered = ee.ImageCollection(
            joined_s1_evi.map(mask_evi, opt_dropNulls=True)
        )

        # filter
        def getddist(image):
            return image.set(
                "dateDist",
                ee.Number(image.get("system:time_start"))
                .subtract(ee.Date(doi.strftime("%Y-%m-%dT%H:%M:%S")).millis())
                .abs(),
            )

        # select pixels with the smalles time gap to doi and mosaic spatially
        doi = self.S1_DATE
        print("here")
        s1_selected = ee.Image(gee_s1_filtered.map(getddist).sort("dateDist").first())

        self.s1_selected = s1_selected

        s1_g0vol = s1_selected.select(["VV_gamma0vol", "VH_gamma0vol"])
        s1_g0surf = s1_selected.select(["VV_gamma0surf", "VH_gamma0surf"])

        if tempfilter == True:
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

            s1_sig0 = s1_sig0_vv.select(["constant"], ["VV"])

        # extract information
        s1_g0vol_vv = s1_g0vol.select("VV_gamma0vol")
        s1_g0vol_vh = s1_g0vol.select("VH_gamma0vol")
        s1_g0surf_vv = s1_g0surf.select("VV_gamma0surf")
        s1_g0surf_vh = s1_g0surf.select("VH_gamma0surf")

        # calculate statistical moments
        gee_s1_filtered = gee_s1_filtered.filterDate(
            str(doi.year) + "-01-01", str(doi.year) + "-12-31"
        )  # .select('VV_gamma0vol')
        gee_s1_lin = gee_s1_filtered.map(tolin)

        # check if median was alread computed
        # tmpcoords = self.roi.getInfo()['coordinates']
        # mean_asset_path = 's1med_' + str(abs(tmpcoords[0][0][0])) + \
        #                   '_' + str(abs(tmpcoords[0][0][1])) + '_' + \
        #                   str(abs(tmpcoords[0][2][0])) + \
        #                   '_' + str(abs(tmpcoords[0][2][1])) + \
        #                   '_' + str(self.sampling) + '_' + str(self.TRACK_NR) + '_' + str(doi.year)
        # mean_asset_path = mean_asset_path.replace('.', '')
        # mean_gvv_v = ee.Image('users/felixgreifeneder/' + mean_asset_path)
        # try:
        #     mean_gvv_v.getInfo()
        #     print('S1 median exists')
        # except:
        # compute median
        mean_gvv_v = ee.Image(
            gee_s1_lin.select("VV_gamma0vol").reduce(
                ee.Reducer.median(), parallelScale=16
            )
        )
        mean_gvh_v = ee.Image(
            gee_s1_lin.select("VH_gamma0vol").reduce(
                ee.Reducer.median(), parallelScale=16
            )
        )
        mean_gvv_s = ee.Image(
            gee_s1_lin.select("VV_gamma0surf").reduce(
                ee.Reducer.median(), parallelScale=16
            )
        )
        mean_gvh_s = ee.Image(
            gee_s1_lin.select("VH_gamma0surf").reduce(
                ee.Reducer.median(), parallelScale=16
            )
        )

        # export asset
        # self.GEE_2_asset(raster=mean_gvv_v, name=mean_asset_path, timeout=False, outdir='')
        # mean_gvv_v = ee.Image('users/felixgreifeneder/' + mean_asset_path)

        # std_gvv_v = ee.Image(gee_s1_lin.select('VV_gamma0vol').reduce(ee.Reducer.stdDev(), parallelScale=24))
        # g0 - surf
        k1gvv_v = ee.Image(
            gee_s1_filtered.select("VV_gamma0vol").reduce(
                ee.Reducer.mean(), parallelScale=24
            )
        )
        k1gvh_v = ee.Image(
            gee_s1_filtered.select("VH_gamma0vol").reduce(
                ee.Reducer.mean(), parallelScale=24
            )
        )
        k2gvv_v = ee.Image(
            gee_s1_filtered.select("VV_gamma0vol").reduce(
                ee.Reducer.stdDev(), parallelScale=24
            )
        )
        k1gvh_s = ee.Image(
            gee_s1_filtered.select("VH_gamma0surf").reduce(
                ee.Reducer.mean(), parallelScale=24
            )
        )
        k2gvv_s = ee.Image(
            gee_s1_filtered.select("VV_gamma0surf").reduce(
                ee.Reducer.stdDev(), parallelScale=24
            )
        )
        k2gvh_s = ee.Image(
            gee_s1_filtered.select("VH_gamma0surf").reduce(
                ee.Reducer.stdDev(), parallelScale=24
            )
        )
        # k3gvv_s = ee.Image(gee_s1_ln.select('VV_gamma0surf').reduce(ee.Reducer.skew(), parallelScale=24))
        # k4gvv_s = ee.Image(gee_s1_ln.select('VV_gamma0surf').reduce(ee.Reducer.kurtosis(), parallelScale=24))
        # mean_gvv_s = ee.Image(gee_s1_lin.select('VV_gamma0surf').reduce(ee.Reducer.mean(), parallelScale=24))
        # std_gvv_s = ee.Image(gee_s1_lin.select('VV_gamma0surf').reduce(ee.Reducer.stdDev(), parallelScale=24))

        # if dualpol == True:
        #     # s0
        #     k1vh = ee.Image(gee_s1_ln.select('VH_sigma0').reduce(ee.Reducer.mean(), parallelScale=24))
        #     k2vh = ee.Image(gee_s1_ln.select('VH_sigma0').reduce(ee.Reducer.stdDev(), parallelScale=24))
        #     k3vh = ee.Image(gee_s1_ln.select('VH_sigma0').reduce(ee.Reducer.skew(), parallelScale=24))
        #     k4vh = ee.Image(gee_s1_ln.select('VH_sigma0').reduce(ee.Reducer.kurtosis(), parallelScale=24))
        #     mean_vh = ee.Image(gee_s1_lin.select('VH_sigma0').reduce(ee.Reducer.mean(), parallelScale=24))
        #     std_vh = ee.Image(gee_s1_lin.select('VH_sigma0').reduce(ee.Reducer.stdDev(), parallelScale=24))
        #     # g0 - vol
        #     k1gvh_v = ee.Image(gee_s1_ln.select('VH_gamma0vol').reduce(ee.Reducer.mean(), parallelScale=24))
        #     k2gvh_v = ee.Image(gee_s1_ln.select('VH_gamma0vol').reduce(ee.Reducer.stdDev(), parallelScale=24))
        #     k3gvh_v = ee.Image(gee_s1_ln.select('VH_gamma0vol').reduce(ee.Reducer.skew(), parallelScale=24))
        #     k4gvh_v = ee.Image(gee_s1_ln.select('VH_gamma0vol').reduce(ee.Reducer.kurtosis(), parallelScale=24))
        #     mean_gvh_v = ee.Image(gee_s1_lin.select('VH_gamma0vol').reduce(ee.Reducer.mean(), parallelScale=24))
        #     std_gvh_v = ee.Image(gee_s1_lin.select('VH_gamma0vol').reduce(ee.Reducer.stdDev(), parallelScale=24))
        #     # g0 - surf
        #     k1gvh_s = ee.Image(gee_s1_ln.select('VH_gamma0surf').reduce(ee.Reducer.mean(), parallelScale=24))
        #     k2gvh_s = ee.Image(gee_s1_ln.select('VH_gamma0surf').reduce(ee.Reducer.stdDev(), parallelScale=24))
        #     k3gvh_s = ee.Image(gee_s1_ln.select('VH_gamma0surf').reduce(ee.Reducer.skew(), parallelScale=24))
        #     k4gvh_s = ee.Image(gee_s1_ln.select('VH_gamma0surf').reduce(ee.Reducer.kurtosis(), parallelScale=24))
        #     mean_gvh_s = ee.Image(gee_s1_lin.select('VH_gamma0surf').reduce(ee.Reducer.mean(), parallelScale=24))
        #     std_gvh_s = ee.Image(gee_s1_lin.select('VH_gamma0surf').reduce(ee.Reducer.stdDev(), parallelScale=24))

        # export
        # self.S1_SIG0_VV_db = s1_sig0_vv
        self.S1_G0VOL_VV_db = s1_g0vol_vv
        self.S1G0VOLMEAN_VV = (
            ee.Image(10).multiply(mean_gvv_v.log10()).copyProperties(mean_gvv_v)
        )
        self.S1_G0VOL_VH_db = s1_g0vol_vh
        self.S1G0VOLMEAN_VH = (
            ee.Image(10).multiply(mean_gvh_v.log10()).copyProperties(mean_gvh_v)
        )
        self.S1_G0SURF_VV_db = s1_g0surf_vv
        self.S1_G0SURF_VH_db = s1_g0surf_vh
        self.S1G0SURFMEAN_VV = (
            ee.Image(10).multiply(mean_gvv_s.log10()).copyProperties(mean_gvv_s)
        )
        self.S1G0SURFMEAN_VH = (
            ee.Image(10).multiply(mean_gvh_s.log10()).copyProperties(mean_gvh_s)
        )
        self.K1G0VV_V = k1gvv_v
        self.K1G0VH_V = k1gvh_v
        self.K2G0VV_V = k2gvv_v
        self.K1G0VH_S = k1gvh_s
        self.K2G0VV_S = k2gvv_s
        self.K2G0VH_S = k2gvh_s

    def estimate_SM_GBR_1step(self):
        # load GBR models
        from pysmm.no_GLDAS_decisiontree_GEE__1step_w_grapex_data import (
            tree as GBR_tree,
        )
        import sys

        g0_v_vv = self.S1_G0VOL_VV_db
        g0_v_vh = self.S1_G0VOL_VH_db
        g0_s_vv = self.S1_G0SURF_VV_db
        g0_s_vh = self.S1_G0SURF_VH_db
        dg0_v_vv = g0_v_vv.subtract(self.S1G0VOLMEAN_VV)
        dg0_v_vh = g0_v_vh.subtract(self.S1G0VOLMEAN_VH)
        dg0_s_vv = g0_s_vv.subtract(self.S1G0SURFMEAN_VV)
        dg0_s_vh = g0_s_vh.subtract(self.S1G0SURFMEAN_VH)
        g0_v_vv_k1 = self.K1G0VV_V
        g0_v_vh_k1 = self.K1G0VH_V
        g0_v_vv_k2 = self.K2G0VV_V
        g0_s_vh_k1 = self.K1G0VH_S
        g0_s_vv_k2 = self.K2G0VV_S
        g0_s_vh_k2 = self.K2G0VH_S
        crops = self.CROPS_COVER
        grass = self.GRASS_COVER
        moss = self.MOSS_COVER
        l8b1 = self.L8_IMG.select("B1")
        l8b2 = self.L8_IMG.select("B2")
        l8b2med = self.L8_MEAN.select("B2_median")
        l8b3 = self.L8_IMG.select("B3")
        l8b3med = self.L8_MEAN.select("B3_median")
        l8b4 = self.L8_IMG.select("B4")
        l8b4med = self.L8_MEAN.select("B4_median")
        l8b5 = self.L8_IMG.select("B5")
        l8b5med = self.L8_MEAN.select("B5_median")
        l8b6 = self.L8_IMG.select("B6")
        l8b6med = self.L8_MEAN.select("B6_median")
        l8b7 = self.L8_IMG.select("B7")
        l8b10 = self.L8_IMG.select("B10")
        l8b10med = self.L8_MEAN.select("B10_median")
        l8b11 = self.L8_IMG.select("B11")
        l8dt = self.L8_DDATE
        ndvi = self.EVI_IMG
        ndvi_med = self.EVI_MEAN
        bulk = self.BULK
        clay = self.CLAY
        sand = self.SAND

        input_image1 = ee.Image(
            [
                dg0_v_vv.toFloat(),
                dg0_v_vh.toFloat(),
                g0_s_vv.toFloat(),
                dg0_s_vv.toFloat(),
                g0_v_vv_k1.toFloat(),
                g0_s_vh_k2.toFloat(),
                crops.toFloat(),
                grass.toFloat(),
                moss.toFloat(),
                l8b1.toFloat(),
                l8b4.toFloat(),
                l8b5.toFloat(),
                l8b6.toFloat(),
                l8b6med.toFloat(),
                l8dt.toFloat(),
                ndvi.toFloat(),
                ndvi_med.toFloat(),
                bulk.toFloat(),
                clay.toFloat(),
                sand.toFloat(),
            ]
        )

        input_image1 = input_image1.rename(
            [
                "dg0_v_vv",
                "dg0_v_vh",
                "g0_s_vv",
                "dg0_s_vv",
                "k1_v_vv",
                "k2_s_vh",
                "crops",
                "grass",
                "moss",
                "l8b1",
                "l8b4",
                "l8b5",
                "l8b6",
                "l8b6_med",
                "l8dt",
                "ndvi",
                "ndvi_med",
                "bulk",
                "clay",
                "sand",
            ]
        )

        ipt_img_mask1 = input_image1.mask().reduce(ee.Reducer.allNonZero())

        combined_mask = ipt_img_mask1

        input_image1 = input_image1.updateMask(ee.Image(combined_mask))

        sys.setrecursionlimit(5000)
        estimated_smc = GBR_tree(input_image1)
        estimated_smc = estimated_smc.updateMask(combined_mask)

        # mask negative values
        estimated_smc = estimated_smc.updateMask(estimated_smc.gt(0))

        ## scaling
        estimated_smc = estimated_smc.multiply(100).round().int8()

        self.ESTIMATED_SM = estimated_smc.rename(["ESTIMATED_SM"]).set(
            {
                "system:time_start": ee.Date(
                    self.S1_DATE.strftime("%Y-%m-%dT%H:%M:%S")
                ).millis(),
                "s1tracknr": int(self.TRACK_NR),
            }
        )
        self.ESTIMATED_MEAN_SM = None

    def get_S1_dates(
        self,
        tracknr=None,
        dualpol=True,
        ascending=True,
        start="2014-01-01",
        stop="2020-01-01",
    ):
        # load S1 data
        gee_s1_collection = ee.ImageCollection("COPERNICUS/S1_GRD")

        # ASCENDING acquisitions
        gee_s1_filtered = (
            gee_s1_collection.filter(ee.Filter.eq("instrumentMode", "IW"))
            .filterBounds(self.roi)
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
            .filterDate(start, opt_end=stop)
        )

        if ascending == True:
            # Consider only image from ascending orbits
            gee_s1_filtered = gee_s1_filtered.filter(
                ee.Filter.eq("orbitProperties_pass", "ASCENDING")
            )

        if dualpol == True:
            gee_s1_filtered = gee_s1_filtered.filter(
                ee.Filter.listContains("transmitterReceiverPolarisation", "VH")
            )

        if tracknr is not None:
            if (type(tracknr)) == list:
                gee_s1_filtered = gee_s1_filtered.filter(
                    ee.Filter.inList("relativeOrbitNumber_start", tracknr)
                )
            else:
                gee_s1_filtered = gee_s1_filtered.filter(
                    ee.Filter.eq("relativeOrbitNumber_start", tracknr)
                )

        # create a list of availalbel dates
        tmp = gee_s1_filtered.getInfo()
        tmp_ids = [x["properties"]["system:index"] for x in tmp["features"]]

        dates = np.array(
            [
                dt.datetime(
                    int(x[17:21]),
                    int(x[21:23]),
                    int(x[23:25]),
                    hour=int(x[26:28]),
                    minute=int(x[28:30]),
                )
                for x in tmp_ids
            ]
        )
        orbits = np.array(
            [x["properties"]["relativeOrbitNumber_start"] for x in tmp["features"]]
        )

        return dates, orbits

    def get_S1_tmp_collection(
        self,
        year,
        month,
        day,
        hour,
        minute,
        trackflt=None,
        dualpol=True,
        ascending=False,
        mask_copernicuslc=False,
    ):
        def mosaicByDate(imcol):
            def xf(d):
                d = ee.Date(d)
                im = imcol.filterDate(d, d.advance(1, "day")).mosaic()
                return im.set(
                    "system:time_start", d.millis(), "system:id", d.format("YYYY-MM-dd")
                )

            imlist = imcol.toList(imcol.size())
            unique_dates = imlist.map(
                lambda x: ee.Image(x).date().format("YYYY-MM-dd")
            ).distinct()
            mosaic_imlist = unique_dates.map(xf)
            return ee.ImageCollection(mosaic_imlist)

        def mask_lc_copernicus(image):
            copernicus_collection = ee.ImageCollection(
                "COPERNICUS/Landcover/100m/Proba-V/Global"
            )
            copernicus_image = (
                ee.Image(copernicus_collection.toList(1000).get(0))
                .select("discrete_classification")
                .setDefaultProjection(image.select(1).projection())
                .clip(image.geometry())
            )

            valLClist = [20, 30, 40, 60, 125, 126, 121, 122, 123, 124]

            lcmask = (
                copernicus_image.eq(valLClist[0])
                .bitwiseOr(copernicus_image.eq(valLClist[1]))
                .bitwiseOr(copernicus_image.eq(valLClist[2]))
                .bitwiseOr(copernicus_image.eq(valLClist[3]))
                .bitwiseOr(copernicus_image.eq(valLClist[4]))
                .bitwiseOr(copernicus_image.eq(valLClist[5]))
                .bitwiseOr(copernicus_image.eq(valLClist[6]))
                .bitwiseOr(copernicus_image.eq(valLClist[7]))
                .bitwiseOr(copernicus_image.eq(valLClist[8]))
                .bitwiseOr(copernicus_image.eq(valLClist[9]))
            )
            maskimg = ee.Image.cat([lcmask, lcmask, image.select("angle").mask()])

            # tmp = ee.Image(image)
            # tmp = tmp.updateMask(lcmask)

            return image.updateMask(maskimg)

        gee_s1_collection = ee.ImageCollection("COPERNICUS/S1_GRD")

        # Filter the image collection
        gee_s1_filtered = (
            gee_s1_collection.filter(ee.Filter.eq("instrumentMode", "IW"))
            .filterBounds(self.roi)
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        )
        if ascending:
            # Consider only image from ascending orbits
            gee_s1_filtered = gee_s1_filtered.filter(
                ee.Filter.eq("orbitProperties_pass", "ASCENDING")
            )

        if dualpol:
            # Consider only dual-pol scenes
            gee_s1_filtered = gee_s1_filtered.filter(
                ee.Filter.listContains("transmitterReceiverPolarisation", "VH")
            )

        if trackflt is not None:
            # Specify track
            gee_s1_filtered = gee_s1_filtered.filter(
                ee.Filter.eq("relativeOrbitNumber_start", trackflt)
            )

        if mask_copernicuslc:
            gee_s1_filtered = gee_s1_filtered.map(mask_lc_copernicus)

        # filter
        def getddist(image):
            return image.set(
                "dateDist",
                ee.Number(image.get("system:time_start"))
                .subtract(ee.Date(doi.strftime("%Y-%m-%dT%H:%M:%S")).millis())
                .abs(),
            )

        # select pixels with the smalles time gap to doi and mosaic spatially
        doi = dt.datetime(year=year, month=month, day=day, hour=hour, minute=minute)
        s1_selected = ee.Image(gee_s1_filtered.map(getddist).sort("dateDist").first())
        self.this0 = s1_selected
        self.S1_DATE = dt.datetime.strptime(
            s1_selected.date().format("yyyy-MM-dd HH:mm:ss").getInfo(),
            "%Y-%m-%d %H:%M:%S",
        )

        # get the track number
        s1_sig0_info = s1_selected.getInfo()
        track_nr = s1_sig0_info["properties"]["relativeOrbitNumber_start"]
        self.TRACK_NR = track_nr
        self.ORBIT = s1_sig0_info["properties"]["orbitProperties_pass"]

        # only uses images of the same track
        gee_s1_filtered = gee_s1_filtered.filterMetadata(
            "relativeOrbitNumber_start", "equals", track_nr
        )

        self.this1 = gee_s1_filtered

        # calculate g0
        # paths to dem
        dem = "USGS/SRTMGL1_003"

        # list of models
        model = "volume"
        gee_s1_fltd_vol = self._slope_correction(gee_s1_filtered, ee.Image(dem), model)

        model = "surface"
        gee_s1_fltd_surf = self._slope_correction(gee_s1_filtered, ee.Image(dem), model)

        self.this3 = gee_s1_fltd_vol
        self.this4 = gee_s1_fltd_surf

        gee_s1_filtered = gee_s1_fltd_vol.combine(gee_s1_fltd_surf, overwrite=True)

        self.this6 = gee_s1_filtered

        # apply no data mask
        def mask_no_data(image):
            return image.updateMask(image.select("no_data_mask"))

        # TODO: Modified, removed mask_no_data
        mm = gee_s1_filtered.map(mask_no_data)
        self.mm = mm

        gee_s1_filtered = gee_s1_filtered

        # self.S1_reference_stack = mosaicByDate(gee_s1_filtered)
        self.S1_reference_stack = mosaicByDate(gee_s1_filtered)

    def get_available_S1_tracks(self, dualpol=True):
        # load S1 data
        gee_s1_collection = ee.ImageCollection("COPERNICUS/S1_GRD")

        # ASCENDING acquisitions
        gee_s1_filtered = (
            gee_s1_collection.filter(ee.Filter.eq("instrumentMode", "IW"))
            .filterBounds(self.roi)
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
            .filter(ee.Filter.eq("orbitProperties_pass", "ASCENDING"))
        )
        #           .filter(ee.Filter.eq('platform_number', 'A')) \

        if dualpol == True:
            gee_s1_filtered = gee_s1_filtered.filter(
                ee.Filter.listContains("transmitterReceiverPolarisation", "VH")
            )

        # create a list of availalbel dates
        tmp = gee_s1_filtered.getInfo()
        tmp_tracks = [
            x["properties"]["relativeOrbitNumber_start"] for x in tmp["features"]
        ]
        tracks = np.unique(tmp_tracks)

        return tracks

    def check_gldas_availability(self, year, month, day):
        gldas_test = ee.ImageCollection("NASA/GLDAS/V021/NOAH/G025/T3H").select(
            "SoilMoi0_10cm_inst"
        )
        last_gldas = dt.datetime.strptime(
            gldas_test.aggregate_max("system:index").getInfo(), "A%Y%m%d_%H%M"
        )
        self.LAST_GLDAS = last_gldas
        doi = dt.date(year=year, month=month, day=day)
        return last_gldas.date() > doi

    def get_gldas(self, date=None):
        # get GLDAS, date can be passed as a string or copied from the extracted S1 scene
        if date is None:
            doi = ee.Date(self.S1_DATE.strftime(format="%Y-%m-%d"))

        # check if Sentinel-1 was retrieved and date is available
        if hasattr(self, "S1_DATE"):
            gldas_mean = (
                ee.ImageCollection("NASA/GLDAS/V021/NOAH/G025/T3H")
                .select("SoilMoi0_10cm_inst")
                .filterDate("2014-10-01", dt.datetime.today().strftime("%Y-%m-%d"))
                .filter(
                    ee.Filter.calendarRange(
                        self.S1_DATE.hour, self.S1_DATE.hour + 3, field="hour"
                    )
                )
                .reduce(ee.Reducer.median())
            )
        else:
            gldas_mean = (
                ee.ImageCollection("NASA/GLDAS/V021/NOAH/G025/T3H")
                .select("SoilMoi0_10cm_inst")
                .filterDate("2014-10-01", dt.datetime.today().strftime("%Y-%m-%d"))
                .reduce(ee.Reducer.median())
            )

        gldas_mean = ee.Image(gldas_mean).resample().clip(self.roi)

        # gldas = ee.ImageCollection("NASA/GLDAS/V021/NOAH/G025/T3H") \
        #     .select('SoilMoi0_10cm_inst') \
        #     .filterDate(doi, doi.advance(3, 'hour'))
        #
        # if gldas.size().getInfo() == 0:
        #     print('No GLDAS product for specified date')
        #     gldas_test = ee.ImageCollection("NASA/GLDAS/V021/NOAH/G025/T3H") \
        #                             .select('SoilMoi0_10cm_inst')
        #     last_gldas = gldas_test.aggregate_max('system:index').getInfo()
        #     print('ID of latest available product: ' + last_gldas)
        #     self.GLDAS_IMG = None
        #     self.GLDAS_MEAN = None
        #     return
        #
        # gldas_img = ee.Image(gldas.first()).resample().clip(self.roi)
        gldas_img = gldas_mean

        try:
            self.GLDAS_IMG = gldas_img
            self.GLDAS_MEAN = gldas_mean
        except:
            return None

    def match_l8(self):
        def mask(image):
            # clouds
            def getQABits(image, start, end, newName):
                pattern = 0
                for i in range(start, end + 1):
                    pattern = pattern + int(math.pow(2, i))

                return (
                    image.select([0], [newName]).bitwiseAnd(pattern).rightShift(start)
                )

            def cloud_shadows(image):
                QA = image.select("pixel_qa")
                return getQABits(QA, 3, 3, "Cloud_shadows").eq(0)

            def clouds(image):
                QA = image.select("pixel_qa")
                return getQABits(QA, 5, 5, "Cloud").eq(0)

            # frozen soil / snow
            def frzn(image):
                doi = ee.Date(image.get("system:time_start"))
                snow = (
                    ee.ImageCollection("NASA/GLDAS/V021/NOAH/G025/T3H")
                    .select("SWE_inst")
                    .filterDate(doi, doi.advance(3, "hour"))
                )

                snow_img = ee.Image(snow.first()).resample().clip(self.roi)

                snow_mask = snow_img.expression("(b(0) < 3) ? 1 : 0")

                fs = (
                    ee.ImageCollection("NASA/GLDAS/V021/NOAH/G025/T3H")
                    .select("SoilTMP0_10cm_inst")
                    .filterDate(doi, doi.advance(3, "hour"))
                )

                fs_img = ee.Image(fs.first()).resample().clip(self.roi)

                fs_mask = fs_img.expression("(b(0) > 275) ? 1 : 0")

                return snow_mask.And(fs_mask)

            image = image.updateMask(cloud_shadows(image))
            image = image.updateMask(clouds(image))
            # image = image.updateMask(frzn(image))

            # # radiometric saturation
            # image = image.updateMask(image.select('radsat_qa').eq(2))
            return image.clip(self.roi)

        gee_l8_collection_all = ee.ImageCollection("LANDSAT/LC08/C01/T1_SR")

        # apply landsat mask
        gee_l8_collection_all = gee_l8_collection_all.map(
            mask
        )  # .select(['B4', 'B5', 'B11'])

        def date_mosaic(image):
            def addDate(image2):
                date_img = (
                    ee.Image(image2.date().difference(imdate, "second"))
                    .abs()
                    .float()
                    .rename(["Ddate"])
                    .multiply(-1)
                )
                return image2.addBands(date_img)

            imdate = image.date()

            gee_l8_date = gee_l8_collection_all.filterDate(
                imdate.advance(-40, "day"), imdate.advance(40, "day")
            )
            gee_l8_date = gee_l8_date.map(addDate)
            gee_l8_date = gee_l8_date.qualityMosaic("Ddate").float()

            return gee_l8_date.set("system:time_start", imdate.millis())

        self.L8_STACK = self.S1_reference_stack.map(date_mosaic)
        # self.L8_STACK = gee_l8_collection_all

    def match_evi(self):
        def mask(image):
            # mask image
            # I'm removing the QA band mask because otherwise the image is too much masked
            immask = image.select("SummaryQA")  # .eq(ee.Image(0))
            evimask = image.select("EVI").lte(5000)
            image = image.updateMask(immask).updateMask(evimask)

            return image.clip(self.roi)

        # load collection
        evi_collection = ee.ImageCollection("MODIS/061/MOD13Q1").map(mask).select("EVI")

        def date_mosaic(image):
            def addDate(image2):
                date_img = (
                    ee.Image(image2.date().difference(imdate, "second"))
                    .abs()
                    .float()
                    .rename(["Ddate"])
                    .multiply(-1)
                )
                return image2.addBands(date_img)

            imdate = image.date()

            gee_evi_date = evi_collection.filterDate(
                imdate.advance(-40, "day"), imdate.advance(40, "day")
            )
            gee_evi_date = gee_evi_date.map(addDate)
            gee_evi_date = gee_evi_date.qualityMosaic("Ddate").float()

            return gee_evi_date.set("system:time_start", imdate.millis())

        def band_exists(image):
            band_names = image.bandNames()
            band_exists = band_names.contains("Ddate")
            return image.set("band_exists", band_exists)

        evi_stack = ee.ImageCollection(self.S1_reference_stack.map(date_mosaic))

        self.EVI_STACK = evi_stack.map(band_exists).filter(
            ee.Filter.eq("band_exists", True)
        )

    def match_gldas(self):
        def mask(image):
            return image.clip(self.roi)

        # load collection
        gl_collection = (
            ee.ImageCollection("NASA/GLDAS/V021/NOAH/G025/T3H")
            .select(["SoilTMP0_10cm_inst", "SWE_inst"])
            .filterDate("2014-01-01", dt.datetime.today().strftime("%Y-%m-%d"))
            .map(mask)
        )

        def date_map(image):
            imdate = image.date()

            # filter
            def getddist(image2):
                return image2.set(
                    "dateDist",
                    ee.Number(image2.get("system:time_start"))
                    .subtract(imdate.millis())
                    .abs(),
                )

            # select the image with the smalles time gap
            gl_collection_date = gl_collection.filterDate(
                imdate.advance(-5, "day"), imdate.advance(5, "day")
            )
            gee_gl_date = ee.Image(
                gl_collection_date.map(getddist).sort("dateDist").first()
            )

            return gee_gl_date.set("system:time_start", imdate.millis())

        self.GLDAS_STACK = self.S1_reference_stack.map(date_map)

    def get_l8(self, date=None):
        # get Landsat-8, date can be passed as a string or copied from the extracted S1 scene

        def mask(image):
            # clouds
            def getQABits(image, start, end, newName):
                pattern = 0
                for i in range(start, end + 1):
                    pattern = pattern + int(math.pow(2, i))

                return (
                    image.select([0], [newName]).bitwiseAnd(pattern).rightShift(start)
                )

            def cloud_shadows(image):
                QA = image.select("pixel_qa")
                return getQABits(QA, 3, 3, "Cloud_shadows").eq(0)

            def clouds(image):
                QA = image.select("pixel_qa")
                return getQABits(QA, 5, 5, "Cloud").eq(0)

            # frozen soil / snow
            def frzn(image):
                doi = ee.Date(image.get("system:time_start"))
                snow = (
                    ee.ImageCollection("NASA/GLDAS/V021/NOAH/G025/T3H")
                    .select("SWE_inst")
                    .filterDate(doi, doi.advance(3, "hour"))
                )

                snow_img = ee.Image(snow.first()).resample().clip(self.roi)

                snow_mask = snow_img.expression("(b(0) < 3) ? 1 : 0")

                fs = (
                    ee.ImageCollection("NASA/GLDAS/V021/NOAH/G025/T3H")
                    .select("SoilTMP0_10cm_inst")
                    .filterDate(doi, doi.advance(3, "hour"))
                )

                fs_img = ee.Image(fs.first()).resample().clip(self.roi)

                fs_mask = fs_img.expression("(b(0) > 275) ? 1 : 0")

                return snow_mask.And(fs_mask)

            image = image.updateMask(cloud_shadows(image))
            image = image.updateMask(clouds(image))
            # image = image.updateMask(frzn(image))

            # # radiometric saturation
            # image = image.updateMask(image.select('radsat_qa').eq(2))
            return image.clip(self.roi)

        gee_l8_collection_all = ee.ImageCollection("LANDSAT/LC08/C01/T1_SR")

        # apply landsat mask
        gee_l8_collection = gee_l8_collection_all.map(
            mask
        )  # .select(['B4', 'B5', 'B11'])

        if date is None:
            doi = self.S1_DATE
        else:
            doi = date

        # check if median was alread computed
        tmpcoords = self.roi.getInfo()["coordinates"]
        mean_asset_path = (
            "l8med_"
            + str(abs(tmpcoords[0][0][0]))
            + "_"
            + str(abs(tmpcoords[0][0][1]))
            + "_"
            + str(abs(tmpcoords[0][2][0]))
            + "_"
            + str(abs(tmpcoords[0][2][1]))
            + "_"
            + str(self.sampling)
            + "_"
            + str(doi.year)
        )
        mean_asset_path = mean_asset_path.replace(".", "")
        # gee_l8_mean = ee.Image("projects/ee-felixgreifeneder/assets/" + mean_asset_path)
        # try:
        #     gee_l8_mean.getInfo()
        #     print("L8 median exists")
        # except:
        # compute median
        # TODO l8 median is now based on the current year - 1. This has to be applied also for training
        gee_l8_mean = gee_l8_collection.filterDate(
            str(doi.year - 1) + "-01-01", str(doi.year - 1) + "-12-31"
        ).reduce(ee.Reducer.median(), parallelScale=16)

        # # export asset
        # self.GEE_2_asset(
        #     raster=gee_l8_mean, name=mean_asset_path, timeout=False, outdir=""
        # )
        # gee_l8_mean = ee.Image(
        #     "projects/ee-felixgreifeneder/assets/" + mean_asset_path
        # )

        def addDate(image2):
            date_img = (
                ee.Image(
                    image2.date().difference(
                        doi.strftime("%Y-%m-%dT%H:%M:%S"), "second"
                    )
                )
                .abs()
                .float()
                .rename(["Ddate"])
                .multiply(-1)
            )
            return image2.addBands(date_img)

        # create mosaic for the doi
        gee_l8_date = gee_l8_collection_all.filterDate(
            (doi - dt.timedelta(days=90)).strftime("%Y-%m-%d"),
            (doi + dt.timedelta(days=40)).strftime("%Y-%m-%d"),
        )
        gee_l8_date = gee_l8_date.map(addDate)
        gee_l8_date = gee_l8_date.qualityMosaic("Ddate").float()

        gee_l8_date.set(
            "system:time_start", ee.Date(doi.strftime("%Y-%m-%dT%H:%M:%S")).millis()
        )

        # outimg = gee_l8_mosaic.clip(self.roi)

        try:
            self.L8_IMG = gee_l8_date
            self.L8_MEAN = gee_l8_mean
            self.L8_DDATE = gee_l8_date.select("Ddate").clip(self.roi).multiply(-1)
            self.L8_MASK = self.L8_IMG.mask().reduce(
                ee.Reducer.allNonZero(), parallelScale=8
            )
        except:
            return None

    def get_terrain(self):
        # get SRTM data
        elev = ee.Image("CGIAR/SRTM90_V4").select("elevation").clip(self.roi).resample()
        aspe = (
            ee.Terrain.aspect(ee.Image("CGIAR/SRTM90_V4"))
            .select("aspect")
            .clip(self.roi)
            .resample()
        )
        slop = (
            ee.Terrain.slope(ee.Image("CGIAR/SRTM90_V4"))
            .select("slope")
            .clip(self.roi)
            .resample()
        )
        self.TERRAIN = (elev, aspe, slop)

    def get_modis_evi(self, date=None):
        def create_gldas_snow_frozen_mask(image):
            evi = ee.Image(image.get("primary"))
            gldas = ee.Image(image.get("secondary"))

            mask = ee.Image(
                gldas.expression(
                    "(b('SWE_inst') < 3) && (b('SoilTMP0_10cm_inst') > 275) ? 1 : 0"
                )
            )

            return evi.updateMask(mask)

        def mask(image):
            # mask image

            # I'm removing the QA band mask because otherwise the image is too much masked
            immask = image.select("SummaryQA")  # .eq(ee.Image(0))
            evimask = image.select("EVI").lte(5000)
            image = image.updateMask(immask).updateMask(evimask)

            return image.clip(self.roi)

        # load collection
        evi_collection = ee.ImageCollection("MODIS/061/MOD13Q1").map(mask).select("EVI")

        if date is None:
            doi = self.S1_DATE

        # mask snow frozen from GLDAS and ndvi from
        # join gldas and l8 collections as well as
        # gldas_filt = ee.Filter.equals(leftField='system:time_start', rightField='system:time_start')
        # innjoin = ee.Join.inner()
        # joined_evi_gldas = innjoin.apply(evi_collection, self.GLDAS_STACK, gldas_filt)
        #
        # evi_collection = ee.ImageCollection(joined_evi_gldas.map(create_gldas_snow_frozen_mask))

        # check if median was already calculated
        tmpcoords = self.roi.getInfo()["coordinates"]
        mean_asset_path = (
            "evimed_"
            + str(abs(tmpcoords[0][0][0]))
            + "_"
            + str(abs(tmpcoords[0][0][1]))
            + "_"
            + str(abs(tmpcoords[0][2][0]))
            + "_"
            + str(abs(tmpcoords[0][2][1]))
            + "_"
            + str(self.sampling)
            + "_"
            + str(doi.year)
        )
        mean_asset_path = mean_asset_path.replace(".", "")
        # evi_mean = ee.Image("projects/ee-felixgreifeneder/assets/" + mean_asset_path)
        # try:
        #     evi_mean.getInfo()
        #     print("EVI median exists")
        # except:
        #     # compute avg
        #     # TODO median evi is now based on current year-1 - this has to be implemented also for training
        evi_mean = evi_collection.filterDate(
            str(doi.year - 1) + "-01-01", str(doi.year - 1) + "-12-31"
        ).reduce(ee.Reducer.median(), parallelScale=16)

        # fiter
        # filter
        def addDate(image2):
            date_img = (
                ee.Image(
                    image2.date().difference(
                        doi.strftime("%Y-%m-%dT%H:%M:%S"), "second"
                    )
                )
                .abs()
                .float()
                .rename(["Ddate"])
                .multiply(-1)
            )
            return image2.addBands(date_img)

        gee_evi_date = evi_collection.filterDate(
            (doi - dt.timedelta(days=30)).strftime("%Y-%m-%d"),
            (doi + dt.timedelta(days=30)).strftime("%Y-%m-%d"),
        )
        gee_evi_date = gee_evi_date.map(addDate)
        gee_evi_date = gee_evi_date.qualityMosaic("Ddate").float()

        gee_evi_date.set(
            "system:time_start", ee.Date(doi.strftime("%Y-%m-%dT%H:%M:%S")).millis()
        )

        try:
            self.EVI_IMG = gee_evi_date.select("EVI").clip(self.roi)
            self.EVI_MEAN = evi_mean.select("EVI_median")
        except:
            return None

    def get_bulk_density(self):
        bulkimg = ee.Image(
            "OpenLandMap/SOL/SOL_BULKDENS-FINEEARTH_USDA-4A1H_M/v02"
        ).select("b0")
        self.BULK = bulkimg.resample()

    def get_clay_content(self):
        clayimg = ee.Image(
            "OpenLandMap/SOL/SOL_CLAY-WFRACTION_USDA-3A1A1A_M/v02"
        ).select("b0")
        self.CLAY = clayimg.resample()

    def get_sand_content(self):
        sandimg = ee.Image(
            "OpenLandMap/SOL/SOL_SAND-WFRACTION_USDA-3A1A1A_M/v02"
        ).select("b0")
        self.SAND = sandimg.resample()

    def get_copernicus_lc(self):
        copernicus_collection = ee.ImageCollection(
            "COPERNICUS/Landcover/100m/Proba-V/Global"
        )
        copernicus_image = ee.Image(copernicus_collection.toList(1000).get(0))
        self.LC_ID = copernicus_image.select("discrete_classification")
        self.FOREST_TYPE = copernicus_image.select("forest_type")
        self.BARE_COVER = copernicus_image.select("bare-coverfraction").resample()
        self.CROPS_COVER = copernicus_image.select("crops-coverfraction").resample()
        self.GRASS_COVER = copernicus_image.select("grass-coverfraction").resample()
        self.MOSS_COVER = copernicus_image.select("moss-coverfraction").resample()
        self.SHRUB_COVER = copernicus_image.select("shrub-coverfraction").resample()
        self.TREE_COVER = copernicus_image.select("tree-coverfraction").resample()
        self.URBAN_COVER = copernicus_image.select("urban-coverfraction").resample()
        self.WATERP_COVER = copernicus_image.select(
            "water-permanent-coverfraction"
        ).resample()
        self.WATERS_COVER = copernicus_image.select(
            "water-seasonal-coverfraction"
        ).resample()
