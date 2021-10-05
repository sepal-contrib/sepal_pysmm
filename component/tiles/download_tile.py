from ipywidgets import Output

import ipyvuetify as v

import sepal_ui.sepalwidgets as sw
import sepal_ui.scripts.utils as su

from  component.scripts import download_to_sepal
import component.widget as cw
import component.parameter as param
from component.message import cm

# download_tile = wf.Tile(
#     "download_tile", "GEE Download Task Module", inputs=[download_content]
# )

__all__ = ['DownloadView']

class DownloadView(v.Card):
    
    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.alert = sw.Alert()

        self.w_overwrite = v.Switch(
            v_model=True, inset=True, label="Overwrite SEPAL images"
        )

        self.w_remove = v.Switch(
            v_model=False, inset=True, label="Remove Google Drive Images"
        )

        self.w_selection = cw.PathSelector(param.RAW_DIR, file_type=".txt")

        self.out = Output()
        self.btn = sw.Btn(text="Download", icon="mdi-download")

        self.children = [
            v.CardText(children=[sw.Markdown(cm.download_tile.description)]),
            self.w_selection,
            self.w_overwrite,
            self.w_remove,
            self.btn,
            self.alert,
            self.out,
        ]
        
        self.btn.on_event("click", self.on_download)
    
    @su.loading_button()
    def on_download(self, widget, event, data):

        task_file_name = self.w_selection.get_file_path()

        # Clear old alert messages
        alert.clear()

        with self.out:
            # Clear output if there is something printed before
            self.out.clear_output()
            cs.download_to_sepal.run(
                task_file_name,
                alert,
                overwrite=self.w_overwrite.v_model,
                rmdrive=self.w_remove.v_model,
            )