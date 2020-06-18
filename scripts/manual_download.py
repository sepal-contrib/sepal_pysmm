import os
import subprocess

from ipywidgets import interact, interactive, Layout, HBox, VBox, HTML
import ipywidgets as widgets
from scripts.ipyfilechooser import FileChooser
from scripts import download_to_sepal
import getpass

def export_images(tasks_file_name, overwrite=False, rmdrive=False):
    out_path = os.path.split(tasks_file_name)[0]
    download_to_sepal.run(tasks_file_name, out_path, overwrite, rmdrive)
	

def run(**args):
    tasks_file_name = fc.selected
    overwrite = args['overwrite']
    rmdrive = args['rmdrive']
    if tasks_file_name:
        export_images(tasks_file_name, overwrite, rmdrive)
    else:
        print(f'Please select a task file...')

def start():
    fc.observe(run)
    w_run = interactive(run, {'manual':True}, overwrite=w_overwrite, rmdrive=w_rm_gdrive)
    w_run_button = w_run.children[-2]
    w_run_button.description = 'Download images'
    w_run_button.button_style = 'success'
    w_run_button.icon = 'check'
    display(HTML(html_header))
    display(fc)
    display(VBox([w_run.children[0], w_run.children[1], w_run_button]))
    display(HBox([w_run.children[-1]]))
    
    
w_overwrite = widgets.Checkbox(
    value=False,
    description='Overwrite SEPAL images',
    indent=False,
    disabled=False
)

w_rm_gdrive = widgets.Checkbox(
    value=False,
    description='Remove Google Drive images',
    indent=False,
    disabled=False
)
html_header = """
<style>
.widget-html span {
    color:black!important;
}
div.output_stderr{
    color:none;
}
</style>
<center><h1><b>GEE Download Task Module</b></h1></center>
<p>With this module you can track and download the images processed into your Google Earth Engine account 
by providing the 'tasks' text file, the results will be stored directly into your SEPAL account.</br>
<b>Note that if you check the overwrite and remove options, the results cannot be undone.</b>
</p>
"""

user = getpass.getuser()
fc = FileChooser(f'/home/{user}/')

change_b = fc.children[-1].children[0]
change_b.button_style='info'

cancel_b = fc.children[-1].children[1]
cancel_b.button_style='danger'