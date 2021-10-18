#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
from sepal_ui import mapping
from traitlets import HasTraits, Unicode

import ee
ee.Initialize()


class Aoi_IO(HasTraits):

    asset_id = Unicode('').tag(sync=True)
    column = Unicode('').tag(sync=True)

    
    def __init__(self, asset_id=None):
        """Initiate the Aoi object.

        Args:
            alert_widget (SepalAlert): Widget to display alerts.

        """

        # GEE parameters
        self.selected_feature = None
        self.field = None

        if asset_id:
            self.asset_id = asset_id

        #set up your inputs
        self.file_input = None
        self.file_name = 'Manual_{0}'.format(datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        self.country_selection = None
        self.selection_method = None
        self.drawn_feat = None

        
    def get_aoi_ee(self):

        """ Returns an ee.asset from self

        return: ee.Object

        """
        return ee.FeatureCollection(self.asset_id)
    
    def get_columns(self):

        """ Retrieve the columns or variables from self

        return: sorted list cof column names
        """
        
        aoi_ee = self.get_aoi_ee()
        columns = ee.Feature(aoi_ee.first()).propertyNames().getInfo()
        columns = sorted([col for col in columns if col not in ['system:index', 'Shape_Area']])
        
        return columns
    
    def get_fields(self, column=None):
        """" Retrieve the fields from the selected self column
        
        Args:
            column (str) (optional): Used to query over the asset
        
        return: sorted list of fields

        """

        if not column:
            column = self.column

        aoi_ee = self.get_aoi_ee()
        fields = sorted(aoi_ee.distinct(column).aggregate_array(column).getInfo())

        return fields

    def get_selected_feature(self):
        """ Select a ee object based on the current state.

        Returns:
            ee.geometry

        """

        if not self.column or not self.field:
            self.alert.add_msg('error', f'You must first select a column and a field.')
            raise ValueError

        ee_asset = self.get_aoi_ee()
        select_feature = ee_asset.filterMetadata(self.column, 'equals', self.field).geometry()

        # Specify the selected feature
        self.selected_feature = select_feature

        return select_feature

    def clear_selected(self):
        self.selected_feature = None

    def clear_attributes(self):

        # GEE parameters
        self.column = ""
        self.field = None
        self.selected_feature = None

        #set up your inputs
        self.file_input = None
        self.file_name = 'Manual_{0}'.format(datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        self.country_selection = None
        self.selection_method = None
        self.drawn_feat = None

    def get_not_null_attrs(self):
        return dict((k, v) for k, v in self.__dict__.items() if v is not None)

    def display_on_map(self, map_, dc, asset_ee):
        """ Display the current feature on a map

        Args:

            map_ (SepalMap): Map to display the element
            dc: drawing controls
            asset_ee: GEE Object

        """

        # Search if there is a selected feature, otherwise use all the asset_id


        bounds = self.get_bounds(asset_ee, cardinal=True)
        map_.update_map(asset_ee, bounds=bounds, remove_last=True)


