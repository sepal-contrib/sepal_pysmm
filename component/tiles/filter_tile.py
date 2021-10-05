from ipywidgets import Output
import ipyvuetify as v

import sepal_ui.sepalwidgets as sw
import sepal_ui.scripts.utils as su

import component.widget as cw
from component.message import cm
import component.parameter as param

from component.scripts.filter_closing_smm import run_filter 

class FilterTile(v.Card):
    
    def __init__(self, model, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        self.output = Output()
        self.btn = sw.Btn("Start")
        self.alert = sw.Alert()
        self.w_selector = cw.PathSelector(param.RAW_DIR)
        
        self.children = [
            v.CardTitle(children=[sw.Markdown(cm.filter_tile.title)]),
            v.CardText(children=[sw.Markdown(cm.filter_tile.desc)]),
            self.w_selector,
            self.btn,
            self.alert,
            self.output
        ]
        
        self.btn.on_event('click', self.on_click)
    
    @su.loading_button()
    def on_click(self, widget, event, data):

        # Get the current path
        process_path = self.w_selector.get_current_path()
        
        with self.output:
            self.output.clear_output()

            run_filter(process_path,self.alert)
