#!/usr/bin/env python3

import os

user = getpass.getuser()

RAW_PATH = f'/home/{user}/pysmm_downloads/0_raw/'

if not os.path.exists(RAW_PATH):
    os.makedirs(RAW_PATH)

PROCESSED_PATH = RAW_PATH.replace('0_raw','1_processed')

if not os.path.exists(PROCESSED_PATH):
    os.makedirs(PROCESSED_PATH)

cores = os.cpu_count()


desc_postprocess =  """<p style="line-height: 20px">After the data is filtered, a time series analysis of the soil moisture maps can be performed. Several statistics can be applied whether to the entire time series or to a specified range, statistics as median, mean, standard deviation or linear trend (slope of the line) are available to process the selected data.  </br>The slope of the linear trend, indicates if the trend in soil moisture is negative or positive. These trends might be related to peatland management practices. 
After the processing completes, download the outputs and check them in a GIS environment such as QGIS or ArcGIS.</p>"""

no_images_to_process = """<p style="line-height: 20px">There are no images to process.</p>"""


def closing_filter(process_path, alert):
    
    IMAGES_TYPES = ('.tif')
    folder = process_path
    image_files = []
    if os.path.isdir(folder):
        for root, dirs, files in os.walk(folder):
            if len(files) != 0:
                files = [os.path.join(root, x) for x in files if x.endswith(IMAGES_TYPES)]
                [image_files.append(os.path.abspath(file)) for file in files]
        image_files.sort()
    
    else:
        alert.add_msg(f'ERROR: The {folder} is not a directory path.', type_='error')
    
    if len(image_files) > 0:
        dimension = get_dimension(image_files[0])
        alert.add_msg(f'There are {len(image_files)} images to process, please wait...', type_='info')
        print(f'The image dimension is {dimension[0]} x {dimension[1]} px')

    else:
        return 1

    for i in trange(len(image_files)):
        cfilter.raw_to_processed(image_files[i])

    return 0




class PathSelector(v.Layout, HasTraits):
    
    column = Unicode()
    field = Unicode()
    
    def __init__(self, raw_path, **kwargs):

        self.raw_path = raw_path
        
        super().__init__(**kwargs)

        self.class_="pa-5"
        self.row=True
        self.align_center=True
        self.children = [self._column_widget(),self._field_widget(),]

    def return_paths(self, column=""):
        
        """ Create a list of folders in a given path
        skipping those with begin with '.' or are empty

        """
        search_path = os.path.join(self.raw_path, column)
        paths = [folder for folder in os.listdir(search_path) 
                 if os.path.isdir(os.path.join(search_path, folder)) and not folder.startswith('.') 
                 and len(os.listdir(os.path.join(search_path, folder))) != 0
        ]
        paths.sort()

        return paths
    
    @observe('column')
    def on_column(self, change):
        options = self.return_paths(column=self.column)
        self.children[1].items=options

    def _field_widget(self):
        
        w_field = v.Select(
            v_model=None,
            class_='pa-5', 
            label='Select field...')
        
        def on_change(change):
            self.field = change['new']

        w_field.observe(on_change, 'v_model')
        
        return w_field

    def _column_widget(self):

        w_column = v.Select(
            v_model=None, 
            class_='pa-5 ', 
            label='Select column...',
            items=self.return_paths(),
        )

        def on_change(change):
            self.column = change['new']

        w_column.observe(on_change, 'v_model')

        return w_column


def close_filter_tile():

    select_1.observe(get_select2, )




