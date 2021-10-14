from pathlib import Path
from ipywidgets import Output, Layout
import ipyvuetify as v

import sepal_ui.sepalwidgets as sw
import sepal_ui.scripts.utils as su

import component.widget as cw
from component.message import cm
import component.parameter as param

from component.scripts.filter_closing_smm import run_filter 

class FilterTile(v.Card):
    
    def __init__(self, model, *args, **kwargs):
        
        self.min_height = "900px"
        self.class_='pa-2'
        
        super().__init__(*args, **kwargs)
        
        self.output = Output()
        self.btn = sw.Btn("Apply morphological filter", class_='mb-2')
        self.folder_alert = sw.Alert(children=["Please select a folder with images to process."]).show()
        self.alert = sw.Alert()
        self.w_selector = cw.FolderSelector(param.RAW_DIR)
        
        self.children = [
            v.CardTitle(children=[sw.Markdown(cm.filter_tile.title)]),
            v.CardText(children=[sw.Markdown(cm.filter_tile.desc)]),
            v.Row(
                children=[
                    v.Col(children=[
                        v.Card(
                            children=[
                                v.CardTitle(children=["Select a folder"]),
                                self.folder_alert,
                                self.w_selector
                            ]
                        )
                    ]),
                    v.Col(children=[
                        v.Card(
                            children=[
                                v.CardTitle(children=["Process"]),
                                self.btn,
                                self.output,
                                self.alert
                            ]
                        )
                    ])
                ]                
            )
        ]
        
        self.btn.on_event('click', self.on_click)
        
        self.w_selector.observe(self.get_image_number, 'v_model')
    
    @su.switch("loading", on_widgets=["w_selector"])
    def get_image_number(self, change):
        """Get the number of images in the current path list"""
        
        if change["new"]:
            
            number_of_images = sum([
                len(list(Path(folder).glob("[!.]*.tif"))) for folder in change["new"]
            ])
            
            self.folder_alert.add_msg(f"There are {number_of_images} images in the selected folder(s).")
        else:
            
            self.folder_alert.add_msg(f"Please select a folder with images to process.")
            

    @su.loading_button()
    def on_click(self, widget, event, data):
      
        run_filter(self.w_selector.v_model, self.alert, self.output)
        
        self.alert.add_msg(f'All the images were correctly processed.', type_='success')

