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
        self.alert = sw.Alert()
        
        w_selector_view = cw.FolderSelectorView(folder=param.RAW_DIR, max_depth=0)
        self.w_selector = w_selector_view.w_selector
        
        self.children = [
            v.CardTitle(children=[sw.Markdown(cm.filter_tile.title)]),
            v.CardText(children=[sw.Markdown(cm.filter_tile.desc)]),
            v.Row(
                children=[
                    v.Col(children=[w_selector_view,]),
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

    @su.loading_button()
    def on_click(self, widget, event, data):
      
        run_filter(self.w_selector.v_model, self.alert, self.output)
        
        self.alert.add_msg(f'All the images were correctly processed.', type_='success')

