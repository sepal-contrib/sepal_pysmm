#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from glob import glob
from ipyvuetify import Container
from traitlets import HasTraits, Unicode, observe

class PathSelector(Container, HasTraits):
    """Display select widgets and allows to select
    a specific element from the list.
    """
    
    column = Unicode().tag(sync=True)
    field = Unicode().tag(sync=True)
    task = Unicode().tag(sync=True)
    
    def __init__(self, raw_path='/home/', file_type=None, **kwargs):

        self.raw_path = raw_path
        
        super().__init__(**kwargs)

        self.align_center=True
        self.children = [Row(children=[
            Col(
                children=[self._column_widget()]
            ),
            Col(
                children=[self._field_widget()]
            ),
        ])]

        self.file_type = file_type

        if self.file_type:
            
            self.children = [Row(children=[
                Col(
                    children=[self._column_widget()]
                ),
                Col(
                    children=[self._field_widget()]
                ),
                Col(
                    children=[self._task_widget()]
                )
            ])]


    def widget_column(self):
        return self.children[0].children[0].children[0]

    def widget_field(self):
        return self.children[0].children[1].children[0]

    def widget_task(self):
        return self.children[0].children[2].children[0]

    def return_paths(self):
        
        """ Create a list of folders in a given path
        skipping those with begin with '.' or are empty

        """
        search_path = os.path.join(self.raw_path, self.column)
        paths = [folder for folder in os.listdir(search_path) 
                 if os.path.isdir(os.path.join(search_path, folder)) and not folder.startswith('.') 
                 and len(os.listdir(os.path.join(search_path, folder))) != 0
        ]
        paths.sort()

        return paths


    def return_files(self):
        
        """ Create a list of files in a given path
        skipping those with begin with '.' or are empty

        """
        search_path = os.path.join(self.raw_path, self.column, self.field)
        files = sorted([os.path.split(path)[1] for path in glob(f'{search_path}/*{self.file_type}')])
        
        return files
    
    @observe('column')
    def _on_column(self, change):

        options = self.return_paths()
        self.widget_field().items=options

    @observe('field')
    def _on_field(self, change):
        self.task=''
        if self.file_type:
            options = self.return_files()
            self.widget_task().items=options

    def _task_widget(self):
        
        w_task = Select(
            v_model=None,
            label='Select task file...')
        
        def on_change(change):
            self.task = change['new']

        w_task.observe(on_change, 'v_model')
        
        return w_task

    def _field_widget(self):
        
        w_field = Select(
            v_model=None,
            label='Select field...')
        
        def on_change(change):
            self.field = change['new']

        w_field.observe(on_change, 'v_model')
        
        return w_field

    def _column_widget(self):

        w_column = Select(
            v_model=None, 
            label='Select column...', 
            items=self.return_paths(),
        )

        def on_change(change):
            self.column = change['new']

        w_column.observe(on_change, 'v_model')

        return w_column
    
    def get_current_path(self):
        
        current_path = os.path.join(self.raw_path,
                                    self.column, 
                                   self.field)
        return current_path

    def get_column_path(self):
        
        column_path = os.path.join(self.raw_path,
                                    self.column)
        return column_path

    def get_file_path(self):

        file_path = os.path.join(self.raw_path,
                                self.column,
                                self.field,
                                self.task)
        return file_path