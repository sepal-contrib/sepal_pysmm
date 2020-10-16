#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from glob import glob
from pathlib import Path
import ipyvuetify as v
from traitlets import HasTraits, Unicode, List, observe, link

from functools import partial
from .styles.styles import *


class SepalWidget(v.VuetifyWidget):
    
    def __init__(self, **kwargs):
        
        super().__init__(**kwargs)
        self.viz = True
        
    def toggle_viz(self):
        """toogle the visibility of the widget"""
        if self.viz:
            self.hide()
        else:
            self.show()
        
        return self
    
    def hide(self):
        """add the d-none html class to the widget"""
        if not 'd-none' in str(self.class_):
            self.class_ = str(self.class_).strip() + ' d-none'
        self.viz = False
        
        return self
        
    def show(self):
        """ remove the d-none html class to the widget"""
        if 'd-none' in str(self.class_):
            self.class_ = str(self.class_).replace('d-none', '')
        self.viz = True
        
        return self

class Alert(v.Alert, SepalWidget):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.children = ['']
        self.type = 'info'
        self.text = True
        self.clear()
    
    def add_msg(self, msg, type_='info'):
        self.show()
        self.type = type_
        self.children = [msg]
        
    def clear(self):
        self.hide()
        self.children = ['']


class Btn(v.Btn, SepalWidget):
    """
    Creates a process button filled with the provided text
    
    Returns: 
        btn (v.Btn) :
    """
    

    def __init__(self, text='Button', icon=None, visible=True, **kwargs):
        super().__init__(**kwargs)
        self.color='primary'
        
        if icon:
            self.children=[self.set_icon(icon), text]
        else:
            self.children=[text]

        if not visible:
            self.hide()



    def set_icon(self, icon):

        common_icons = {
            'default' : 'mdi-adjust',
            'download' : 'mdi-download'
        }
        
        if icon in common_icons.keys():
            icon = common_icons[icon]
        
        return v.Icon(left=True, children=[icon])    

    def disable(self):
        self.disabled = True
        
    def activate(self):
        self.loading = False
        self.disabled = False
        
    def on_loading(self):
        self.loading = True


class VueDataFrame(v.VuetifyTemplate):
    """
    Vuetify DataTable rendering of a pandas DataFrame
    
    Args:
        data (DataFrame) - the data to render
        title (str) - optional title
    """

    from pandas import DataFrame
    headers = List([]).tag(sync=True, allow_null=True)
    items = List([]).tag(sync=True, allow_null=True)
    search = Unicode('').tag(sync=True)
    title = Unicode('DataFrame').tag(sync=True)
    index_col = Unicode('').tag(sync=True)
    template = Unicode('''
        <template>
          <v-card>
            <v-card-title>
              <span class="title font-weight-bold">{{ title }}</span>
              <v-spacer></v-spacer>
                <v-text-field
                    v-model="search"
                    append-icon="mdi-magnify"
                    label="Search ..."
                    single-line
                    hide-details
                ></v-text-field>
            </v-card-title>
            <v-data-table
                :headers="headers"
                :items="items"
                :search="search"
                :item-key="index_col"
                :footer-props="{'items-per-page-options': [5, 20, 40]}"
            >
                <template v-slot:no-data>
                  <v-alert :value="true" color="error" icon="mdi-alert">
                    Sorry, nothing to display here :(
                  </v-alert>
                </template>
                <template v-slot:no-results>
                    <v-alert :value="true" color="error" icon="mdi-alert">
                      Your search for "{{ search }}" found no results.
                    </v-alert>
                </template>
                <template v-slot:items="rows">
                  <td v-for="(element, label, index) in rows.item"
                      @click=cell_click(element)
                      >
                    {{ element }}
                  </td>
                </template>
            </v-data-table>
          </v-card>
        </template>
        ''').tag(sync=True)
    
    def __init__(self, *args, 
                 data=DataFrame(), 
                 title=None,
                 **kwargs):
        super().__init__(*args, **kwargs)
        
        from json import loads
        data = data.reset_index()
        self.index_col = data.columns[0]
        headers = [{
              "text": col,
              "value": col
            } for col in data.columns]
        headers[0].update({'align': 'left', 'sortable': True})
        self.headers = headers
        self.items = loads(
            data.to_json(orient='records'))
        if title is not None:
            self.title = title

class FileInput(v.Flex, SepalWidget, HasTraits):

    file = Unicode('')
    
    def __init__(self, 
        extentions=['.txt'], 
        folder=os.path.expanduser('~'), 
        label='search file', 
        **kwargs):

        self.extentions = extentions
        self.folder = folder
        
        self.selected_file = v.TextField(
            label='Selected file', 
            class_='ml-5 mt-5',
            v_model=self.file
        )

        self.loading = v.ProgressLinear(
            indeterminate=False, 
            color= COMPONENTS['PROGRESS_BAR']['color']
            )
        
        self.file_list = v.List(
            dense=True, 
            color='grey lighten-4',
            flat=True,
            children=[
                self.loading, 
                v.ListItemGroup(
                    children=self.get_items(),
                    v_model=''
                )
            ]
        )

        self.file_menu = v.Menu(

            min_width=300,
            children=[self.file_list], 
            close_on_content_click=False,
            max_height='300px', 
            v_slots=[{
                'name': 'activator',
                'variable': 'x',
                'children': Btn(icon='mdi-file-search', v_model=False, v_on='x.on', text=label)
        }])
        
        super().__init__(
            row=True,
            class_='d-flex align-center mb-2',
            align_center=True,
            children=[
                self.file_menu,
                self.selected_file,
            ],
            **kwargs
        )
        
        link((self.selected_file, 'v_model'), (self, 'file'))

        def on_file_select(change):
            new_value = change['new']
            if new_value:
                if os.path.isdir(new_value):
                    self.folder = new_value
                    self.change_folder()
                
                elif os.path.isfile(new_value):
                    self.file = new_value

        self.file_list.children[1].observe(on_file_select, 'v_model')
                
    def change_folder(self):
        """change the target folder"""
        #reset files 
        self.file_list.children[1].children = self.get_items()
    

    def get_items(self):
        """return the list of items inside the folder"""

        self.loading.indeterminate = not self.loading.indeterminate
        
        folder = Path(self.folder)

        list_dir = [el for el in folder.glob('*/') 
                        if el.suffix in self.extentions or el.is_dir() 
                        and not el.name.startswith('.')]

        folder_list = []
        file_list = []

        for el in list_dir:
            
            if el.suffix in ICON_TYPES.keys():
                icon = ICON_TYPES[el.suffix]['icon']
                color = ICON_TYPES[el.suffix]['color']
            else:
                icon = ICON_TYPES['DEFAULT']['icon']
                color = ICON_TYPES['DEFAULT']['color']
            
            children = [
                v.ListItemAction(children=[v.Icon(color= color,children=[icon])]),
                v.ListItemContent(children=[v.ListItemTitle(children=[el.stem + el.suffix])]),
            ] 

            if el.is_dir():
                folder_list.append(v.ListItem(value=str(el), children=children))
            else:
                file_size = str(round(Path(el).stat().st_size/(1024*1024),2)) + ' MB'
                children.append(v.ListItemActionText(children=[file_size]))
                file_list.append(v.ListItem(value=str(el), children=children))

        folder_list = sorted(folder_list, key=lambda x: x.value)
        file_list = sorted(file_list, key=lambda x: x.value)

        parent_path = str(folder.parent)
        parent_item = v.ListItem(value=parent_path, children=[
                v.ListItemAction(children=[
                    v.Icon(color=ICON_TYPES['PARENT']['color'],
                           children=[ICON_TYPES['PARENT']['icon']])]),
                v.ListItemContent(children=[v.ListItemTitle(children=[f'..{parent_path}'])]),

            ])

        folder_list.extend(file_list)
        folder_list.insert(0,parent_item)

        self.loading.indeterminate = not self.loading.indeterminate
        return folder_list
    
    def get_parent_path(self):
        """return the list of all the parents of a given path"""
        path_list = [self.folder]
        path = Path(self.folder)

        while  str(path.parent) != path_list[-1]:
            path = path.parent
            path_list.append(str(path))
        
        return path_list