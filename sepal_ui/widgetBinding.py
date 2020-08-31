import sys

from functools import partial

import ipyvuetify as v
import geemap
import ee

from scripts import run_pysmm
from scripts import download_to_sepal
from sepal_ui import mapping

ee.Initialize()

#make the toolbar button clickable 
def displayDrawer(drawer, toggleButton):
    """
    bin the drawer to it's toggleButton
    
    Args:
        drawer (v.navigationDrawer) : the drawer tobe displayed
        toggleButton(v.Btn) : the button that activate the drawer
    """
    def on_click(widget, event, data, drawer):
        drawer.v_model = not drawer.v_model
        
    toggleButton.on_event('click', partial(on_click, drawer=drawer))

#display the appropriate tile
def display_tile(item, tiles):
    """
    display the apropriate tiles when the item is clicked
    
    Args:
        item (v.ListItem) : the item in the drawer that select the active tile
        tiles ([v.Layout]) : the list of all the available tiles in the app
    """
    def on_click(widget, event, data, tiles):
        for tile in tiles:
            if widget._metadata['card_id'] == tile._metadata['mount_id']:
                tile.class_="ma-5 d-inline"
            else:
                tile.class_="ma-5 d-none"
    
    item.on_event('click', partial(on_click, tiles=tiles))


def bind(widget, obj, variable):
    """ 
    bind the variable to the widget
    
    Args:
        widget (v.XX) : an ipyvuetify input element
        obj : the process_io object
        variable (str) : the name of the member in process_io object
    """
    
    def on_change(widget, event, data, obj, variable):
        
        setattr(obj, variable, widget.v_model)
        
    widget.on_event('change', partial(
        on_change,
        obj=obj,
        variable=variable,
    ))
    
def toggle_inputs(input_list, widget_list):
    """
    display only the widgets that are part of the input_list. the widget_list is the list of all the widgets of the tile.
    
    Args:
        input_list ([v.widget]) : the list of input to be display
        widget_list ([v.widget]) : the list of the tile widget
    """
    
    for input_item in widget_list:
        if input_item in input_list:
            input_item.class_ = 'd-inline'
        else:
            input_item.class_ = 'd-none'

    return



def mbind(widget, widget1, obj, attribute):
    
    
    def on_change(widget, event, data, obj, widget1, attribute):
        
        setattr(obj, attribute, widget.v_model)
        widget1.items = obj.get_fields()
        
    widget.on_event('change', partial(
        on_change,
        obj=obj,
        widget1 = widget1,
        attribute=attribute,
    ))


def field_map_bind(widget, obj, attribute, m, dc):
    

    def on_change(widget, event, data, obj, attribute, m, dc):
        
        setattr(obj, attribute, widget.v_model)

        # Given the current aoi attributes, get selected feature.

        selected_feature = obj.get_selected_feature()
        obj.display_on_map(m, dc, selected_feature)
        
        
    widget.on_event('change', partial(
        on_change, 
        obj=obj,
        attribute=attribute,
        m = m,
        dc = dc,
    ))

def ipyw_bind(widget, obj, variable):
    """ 
    bind the variable to the widget
    
    Args:
        widget (v.XX) : an ipyvuetify input element
        obj : the process_io object
        variable (str) : the name of the member in process_io object
    """

    def on_change(widget, event, data, obj, variable):
        
        setattr(obj, variable, widget.value)
        
    widget.on_event('change', partial(
        on_change,
        obj=obj,
        variable=variable,
    ))


def bind_dates(dates_widget, widget_list, obj):

    w_unique_date = widget_list[0] 
    w_ini_date = widget_list[1] 
    w_end_date = widget_list[2]
    w_mmonths = widget_list[3]
    w_myears = widget_list[4]

    def on_change(widget, event, data, widget_list, obj):

        # Every time is clicked, clear the previous selected dates
        obj.clear_dates()

        if widget.v_model == 'Single date':

            toggle_inputs([w_unique_date], widget_list)

        elif widget.v_model == 'Range':
            toggle_inputs([w_ini_date, w_end_date], widget_list)

        elif widget.v_model == 'Season':
            toggle_inputs([w_myears, w_mmonths], widget_list)

        elif widget.v_model == 'All time series':
            toggle_inputs([], widget_list)

    dates_widget.on_event('change', partial(
        on_change,
        widget_list=widget_list,
        obj=obj,
    ))
 


def bindAoiMethod(method_widget, list_input, obj, m, dc, selection_method, alert_box):
    """
    change the display of the AOI selector according to the method selected. will only display the useful one
    
    Args: 
        method_widget (v.select) : the method selector widget 
        list_input ([v.widget]) : the list of all the aoi inputs
        obj (Aoi_IO) : the IO object of the tile
        m (geemap.Map) the map displayed in the tile
        dc (DrawControl) : the drawing control
        selection_method ([str]) : the available selection methods
    """
    
    def on_change(widget, event, data, list_input, obj, m, dc, selection_method, alert_box):
        
        # Clear the current message of the alert box
        alert_box.clear()

        #clearly identify the differents widgets 
        aoi_file_input = list_input[0]
        aoi_file_name = list_input[1]
        aoi_country_selection = list_input[2]


        aoi_asset_name = list_input[3]
        aoi_asset_btn = list_input[4]
        w_asset_column = list_input[5]
        w_asset_field = list_input[6]

        
        setattr(obj, 'selection_method', widget.v_model)
        
        #remove the map 
        try:
            m.remove_control(dc)
        except:
            pass
        dc.clear()
        #toogle the appropriate inputs
        
        
        if widget.v_model == 'Country boundaries': #country selection
            toggle_inputs([aoi_country_selection], list_input)

        elif widget.v_model == 'Draw a shape': #drawing
            toggle_inputs([aoi_file_name], list_input)
            m.add_control(dc)

        elif widget.v_model == 'Upload file': #shp file
            toggle_inputs([aoi_file_input], list_input)

        elif widget.v_model == 'Use GEE asset': #gee asset
            toggle_inputs([aoi_asset_name, aoi_asset_btn], list_input)


            def asset_change_event(widget, event, data, aoi):
                """ Define the behavior of the AOI asset button, filling up 
                    the columns widget.

                """

                # Clear previous selected attributes
                aoi.clear_attributes()

                # Display column and field widgets
                toggle_inputs([w_asset_column, w_asset_field], 
                    [w_asset_column, w_asset_field])


                # Get the aoi columns and fill up the widget
                columns = aoi.get_columns()
                w_asset_column.items = columns

            aoi_asset_btn.on_event('click', partial(asset_change_event, aoi=obj))

    
    method_widget.on_event('change', partial(
        on_change,
        list_input=list_input,
        obj=obj,
        m=m,
        dc=dc, 
        selection_method=selection_method,
        alert_box=alert_box,
    ))
    
    return 

# Handle draw events
def handle_draw(dc, obj, variable, output=None):
    """ 
    handle the drawing of a geometry on a map. The geometry is transform into a ee.featurecollection and send to the variable attribute of obj.
    
    Args: 
        dc (DrawControl) : the draw control on which the drawing will be done 
        obj (obj IO) : any object created for IO of your tile 
        variable (str) : the name of the atrribute of the obj object where to store the ee.FeatureCollection 
        output (v.Alert, optionnal) : the output to display results
        
    """
    def on_draw(self, action, geo_json, obj, variable, output):
        geom = geemap.geojson_to_ee(geo_json, False)
        feature = ee.Feature(geom)
        setattr(obj, variable, ee.FeatureCollection(feature)) 
        
        if output:
            utils.displayIO(output, 'A shape have been drawn')
        
        return 
        
        
    dc.on_draw(partial(
        on_draw,
        obj=obj,
        variable=variable,
        output=output
    ))
    
    return

def bindAoiProcess(btn, io, m, dc, list_method):
    """
    Create an asset in your gee acount and serve it to the map.
    
    Args:
        btn (v.Btn) : the btn that launch the process
        io (Aoi_IO) : the IO of the aoi selection tile
        m (geemap.Map) : the tile map
        dc (drawcontrol) : the drawcontrol
        output (v.Alert) : the alert of the selector tile
        list_method([str]) : the list of the available selections methods
    """
    
    def on_click(widget, event, data, io, m, dc, list_method):
        
        utils.toggleLoading(widget)
        
        #create the aoi asset
        assetId = run_aoi_selection.run_aoi_selection(

            file_input        = io.file_input, 
            file_name         = io.file_name, 
            country_selection = io.country_selection, 
            asset_name        = io.assetId, 
            drawn_feat        = io.drawn_feat,
            drawing_method    = io.selection_method,
            list_method       = list_method, 
        )
        
        #remove the dc
        dc.clear()
        try:
            m.remove_control(dc)
        except:
            pass
        
        #display it on the map
        if assetId:
            mapping.update_map(m, dc, assetId)
            
        utils.toggleLoading(widget)
        
        #add the value to the IO object 
        setattr(io, 'assetId', assetId)
        
        return 
    
    btn.on_event('click', partial(
        on_click,
        io          = io, 
        m           = m, 
        dc          = dc, 
        list_method = list_method
    ))
    
    return


def bin_pysmm_process(aoi, dates, btn, out, alert):

    def on_click(widget, event, data, aoi, dates, out, btn):
        
        # Clear output if there is something printed before
        out.clear_output()

        # Once the button is clicked, disable it
        btn.disable()

        # Clear old alert messages

        alert.clear()

        @out.capture()
        def run_process(aoi, dates):

            run_pysmm.run_pysmm(aoi, dates, alert)

        run_process(aoi, dates)

        # Activate button again
        btn.activate()        

    btn.on_event('click', partial(
        on_click,
        aoi=aoi,
        dates=dates,
        out=out,
        btn=btn,
    ))

    

