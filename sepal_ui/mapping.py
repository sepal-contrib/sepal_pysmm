#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os 
if 'GDAL_DATA' in list(os.environ.keys()): del os.environ['GDAL_DATA']

import string
import random
import collections
import geemap
from ipyleaflet import basemap_to_tiles, ZoomControl, LayersControl, AttributionControl, ScaleControl, DrawControl
import ee 
from haversine import haversine


import xarray_leaflet
import numpy as np
import rioxarray
import xarray as xr
import matplotlib.pyplot as plt
import ipywidgets as widgets
from ipyleaflet import WidgetControl, LocalTileLayer

def random_string(string_length=3):
    """Generates a random string of fixed length. 
    Args:
        string_length (int, optional): Fixed length. Defaults to 3.
    Returns:
        str: A random string
    """
    # random.seed(1001)
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(string_length))

#initialize earth engine
ee.Initialize()


class SepalMap(geemap.Map):


    def __init__(self, **kwargs):

        """  Initialize Sepal Map.

        Args:

            basemap (str): Select one of the Sepal Base Maps available.


        """

        basemap = dict(
            url='http://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
            max_zoom=20,
            attribution='&copy; <a href="http://www.openstreetmap.org/copyright">\
            OpenStreetMap</a> &copy; <a href="http://cartodb.com/attributions">\
            CartoDB</a>',
            name='CartoDB.DarkMatter'
        )

        basemap = basemap_to_tiles(basemap)

        super().__init__(**kwargs, add_google_map=False, basemap=basemap)
        
        self.center = [0,0]
        self.zoom = 2
        
        super().clear_controls()
        
        self.add_control(ZoomControl(position='topright'))
        self.add_control(LayersControl(position='topright'))
        self.add_control(AttributionControl(position='bottomleft'))
        self.add_control(ScaleControl(position='bottomleft', imperial=False))

        # Create output space for raster interaction
        output_r = widgets.Output(layout={'border': '1px solid black'})
        output_control_r = WidgetControl(widget=output_r, position='bottomright')
        self.add_control(output_control_r)

        self.loaded_rasters = {}
        # Define a behavior when ispector checked and map clicked
        def raster_interaction(**kwargs):

            if kwargs.get('type') == 'click' and self.inspector_checked:
                latlon = kwargs.get('coordinates')
                self.default_style = {'cursor': 'wait'}

                local_rasters = [lr.name for lr in self.layers if isinstance(lr, LocalTileLayer)]

                if local_rasters:

                    with output_r: 
                        output_r.clear_output(wait=True)
                    
                        for lr_name in local_rasters:

                            lr = self.loaded_rasters[lr_name]
                            lat, lon = latlon

                            # Verify if the selected latlon is the image bounds
                            if any([lat<lr.bottom, lat>lr.top, lon<lr.left, lon>lr.right]):
                                print('Location out of raster bounds')
                            else:
                                #row in pixel coordinates
                                y = int(((lr.top - lat) / abs(lr.y_res)))

                                #column in pixel coordinates
                                x = int(((lon - lr.left) / abs(lr.x_res)))

                                #get height and width
                                h, w = lr.data.shape
                                value = lr.data[y][x]
                                print(f'{lr_name}')
                                print(f'Lat: {round(lat,4)}, Lon: {round(lon,4)}')
                                print(f'x:{x}, y:{y}')
                                print(f'Pixel value: {value}')
                else:
                    with output_r:
                        output_r.clear_output()

                self.default_style = {'cursor': 'crosshair'}

        self.on_interaction(raster_interaction)

    def get_drawing_controls(self):

        dc = DrawControl(
            marker={},
            circlemarker={},
            polyline={},
            rectangle={'shapeOptions': {'color': '#0000FF'}},
            circle={'shapeOptions': {'color': '#0000FF'}},
            polygon={'shapeOptions': {'color': '#0000FF'}},
         )

        return dc
        
    def remove_local_layer(self, local_layer):

        """ Remove local layer from memory
        """
        if local_layer.name in self.loaded_rasters.keys():
            self.loaded_rasters.pop(local_layer.name)

    def remove_last_layer(self):
        
        if len(self.layers) > 1:
            last_layer = self.layers[-1]
            self.remove_layer(last_layer)

            # If last layer is local_layer, remove it
            if isinstance(last_layer, LocalTileLayer):
                self.remove_local_layer(last_layer)

    def update_map(self, assetId, bounds, remove_last=False):
        """Update the map with the asset overlay and removing the selected drawing controls
        
        Args:
            assetId (str): the asset ID in gee assets
            bounds (list of tuple(x,y)): coordinates of tl, bl, tr, br points
            remove_last (boolean) (optional): Remove the last layer (if there is one) before 
                                                updating the map
        """  
        if remove_last:
            self.remove_last_layer()

        self.set_zoom(bounds, zoom_out=2)
        self.centerObject(ee.FeatureCollection(assetId), zoom=self.zoom)
        self.addLayer(ee.FeatureCollection(assetId), {'color': 'green'}, name='aoi')


    def set_zoom(self, bounds, zoom_out=1):
        """ Get the proper zoom to the given bounds.

        Args:

            bounds (list of tuple(x,y)): coordinates of tl, bl, tr, br points
            zoom_out (int) (optional): Zoom out the bounding zoom

        Returns:

            zoom (int): Zoom for the given ee_asset
        """

        tl, bl, tr, br = bounds
        
        maxsize = max(haversine(tl, br), haversine(bl, tr))
        lg = 40075 #number of displayed km at zoom 1
        zoom = 1
        while lg > maxsize:
            zoom += 1
            lg /= 2

        if zoom_out > zoom:
            zoom_out = zoom - 1

        self.zoom = zoom-zoom_out

    #copy of the geemap add_raster function to prevent a bug from sepal 
    def add_raster(self, image, bands=None, layer_name=None, colormap=None, x_dim='x', y_dim='y', opacity=1.0, center=False):
        """Adds a local raster dataset to the map.
        Args:
            image (str): The image file path.
            bands (int or list, optional): The image bands to use. It can be either a number (e.g., 1) or a list (e.g., [3, 2, 1]). Defaults to None.
            layer_name (str, optional): The layer name to use for the raster. Defaults to None.
            colormap (str, optional): The name of the colormap to use for the raster, such as 'gray' and 'terrain'. More can be found at https://matplotlib.org/3.1.0/tutorials/colors/colormaps.html. Defaults to None.
            x_dim (str, optional): The x dimension. Defaults to 'x'.
            y_dim (str, optional): The y dimension. Defaults to 'y'.
        """
        if not os.path.exists(image):
            print('The image file does not exist.')
            return

        if colormap is None:
            colormap = plt.cm.inferno

        if layer_name is None:
            layer_name = 'Layer_' + random_string()

        if layer_name in self.loaded_rasters.keys():
            layer_name = layer_name+random_string()

        if isinstance(colormap, str):
            colormap = plt.cm.get_cmap(name=colormap)

        da = rioxarray.open_rasterio(image, masked=True)

        # Create a named tuple with raster bounds and resolution
        local_raster = collections.namedtuple(
            'LocalRaster', ('name', 'left', 'bottom', 'right', 'top', 'x_res', 'y_res', 'data')
            )(layer_name, *da.rio.bounds(), *da.rio.resolution(), da.data[0])


        self.loaded_rasters[layer_name] = local_raster


        multi_band = False
        if len(da.band) > 1:
            multi_band = True
            if bands is None:
                bands = [3, 2, 1]
        else:
            bands = 1

        if multi_band:
            da = da.rio.write_nodata(0)
        else:
            da = da.rio.write_nodata(np.nan)
        da = da.sel(band=bands)

        if multi_band:
            layer = da.leaflet.plot(
                self, x_dim=x_dim, y_dim=y_dim, rgb_dim='band')
        else:
            layer = da.leaflet.plot(
                self, x_dim=x_dim, y_dim=y_dim, colormap=colormap)


        layer.name = layer_name

        
        layer.opacity = opacity if abs(opacity) <= 1.0 else 1.0

        if center:
            lat = (local_raster.top-local_raster.bottom)/2 + local_raster.bottom
            lon = (local_raster.right-local_raster.left)/2 + local_raster.left
            

            bounds = ((local_raster.top, local_raster.left),
                      (local_raster.bottom, local_raster.left), 
                      (local_raster.top, local_raster.right), 
                      (local_raster.bottom, local_raster.right))

            self.center = (lat,lon)
            self.set_zoom(bounds)