#!/usr/bin/env python3

from datetime import datetime, date
import numpy as np
import pandas as pd
import geemap
import ipywidgets as widgets
from ipywidgets import interact, HTML, interact_manual, interactive, HBox, VBox

import ee
import matplotlib.pyplot as plt

import logging
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)


ee.Initialize()
aoi_ee = ee.FeatureCollection('users/dafguerrerom/FAO/PYSMM/sipalaga_phu_points')

Map = geemap.Map(center=[-2.12, 113.83], zoom=6)
Map.layout.height='250px'
Map.layout.width='250px'
Map.clear_controls()
Map.add_basemap('Google Satellite')

sipalaga_data = pd.read_pickle('data/pysmm_ts_SIPALAGA_points.pkl')
sipalaga_data = sipalaga_data.set_index('Location')

# Widgets
def create_wpoints(data):
    w_points = widgets.Dropdown(
        options=data.index.values.tolist(),
        value=data.index.values.tolist()[0],
        description='ID:',
        disabled=False,
    )
    return w_points

w_measures = widgets.Dropdown(
    options = ['GWL_max', 'GWL_min', 'GWL_rata', 'SM_max', 'SM_min', 'SM_rata', 'Total'],
    value = 'GWL_max'
)

start_date = datetime(2014, 1, 1)
end_date = date.today()
dates = pd.date_range(start_date, end_date, freq='M')

options = [(date.strftime(' %b %Y '), date) for date in dates]
index = (0, len(options)-1)

w_date_slider = widgets.SelectionRangeSlider(
    options=options,
    index=index,
    description='Dates',
    orientation='horizontal',
    layout={'width': '500px'}
)

w_temp = widgets.Dropdown(
    options=[('Daily', 'd'),('Monthly','m'), ('Yearly','y')],
    value='d',
    description='Group by:',
    disabled=False,
)

def read_measures(csv, id_name, date_name, measure, format_date="%d/%m/%Y", delimiter=";"):
    data = (csv)
    pd_ds = pd.read_csv(data, delimiter=delimiter)
    pd_ds = pd_ds.set_index(pd_ds[id_name])
    pd_ds[date_name] = pd.to_datetime(pd_ds[date_name], format=format_date)
    
    pd_ds=pd_ds.rename(columns = {date_name:'date', id_name:'pid', measure: 'measure'})
    
    return pd_ds

def combine_smm(smm_data, pd_ds):
    df1 = smm_data.copy()
    ds_index = list(pd_ds.index) # Create dataset index list
    
    for _index, row in df1.iterrows():
        if _index in ds_index: # Verify if the point ID exists in the pd_ds info

            df2 = pd_ds.loc[_index] # Create sub df from a given Point ID
            df2 = df2.set_index(df2['date']) # Make date as pd index
            
            df3 = df1.loc[_index]['ts_data'] # Select the corresponding df of the given id_point
            df3.columns = ['smm'] # Rename the column

            df4 = pd.concat([df2,df3], axis=1) # Combine the both df
            df1.at[_index, 'ts_data'] = df4 # Overwrite the ts_data with the df
            
    return df1

pd_sipalaga = read_measures('data/all_data_location_nonan.csv', 
                        'Location', 
                        'date', 
                        'GWL_max',
                        format_date="%Y-%m-%d")
combined_sipalaga = combine_smm(sipalaga_data, pd_sipalaga)

def show_figure(w_date_slider, w_measure, w_points, w_temp):
    
   
    pd_sipalaga = read_measures('data/all_data_location_nonan.csv', 
                            'Location', 
                            'date', 
                            w_measure,
                            format_date="%Y-%m-%d")
    combined_sipalaga = combine_smm(sipalaga_data, pd_sipalaga)
    
    data = combined_sipalaga
    
    ts = data.loc[w_points]['ts_data'][w_date_slider[0]:w_date_slider[1]].groupby(pd.Grouper(freq=w_temp)).mean()

    date = ts.index
    
    field_measure = ts['smm'].interpolate(method='linear')
    smm_measure = ts['measure'].interpolate(method='linear')

    fig,ax = plt.subplots()
    # make a plot
    ax.plot(date, field_measure, color="red", marker="o")
    # set x-axis label
    ax.set_xlabel("year",fontsize=14)
    # set y-axis label
    ax.set_ylabel("Soil Moisture Map",color="red",fontsize=14)
    
    # twin object for two different y-axis on the sample plot
    ax2=ax.twinx()
    # make a plot with different y-axis using second axis object
    ax2.plot(date, smm_measure, color="blue", marker="o")
    ax2.set_ylabel(w_measure, color="blue", fontsize=14)

    # Display Map
    selected_feature = aoi_ee.filterMetadata('Location', 'equals', w_points).geometry()
    square = selected_feature.buffer(ee.Number(10000).sqrt().divide(2), 1).bounds()
    empty = ee.Image().byte();
    outline = empty.paint(featureCollection=square, color=1, width=2)
    Map.addLayer(outline, {'palette': 'FF0000'}, 'edges');
    Map.centerObject(square, zoom=15)
    
def start():
	run_figure = interactive(show_figure, {'manual':True}, 
	                         w_date_slider=w_date_slider, 
	                         w_measure=w_measures, 
	                         w_points=create_wpoints(sipalaga_data), 
	                            w_temp=w_temp)

	run_figure.children[-2].description='Show figure'
	display(HBox([run_figure.children[1],run_figure.children[2], run_figure.children[3]]))
	display(HBox([run_figure.children[0], run_figure.children[-2]]))
	display(HBox([run_figure.children[-1], Map]))