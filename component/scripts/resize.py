from traitlets import Unicode, List, default
from IPython.display import display
import ipyvuetify as v


class ResizeTrigger(v.VuetifyTemplate):
    
    @default("template")
    def _template(self):
        return """
            <script>
                {methods: {
                    jupyter_resize(){
                        console.log("Resizing");
                        window.dispatchEvent(new Event('resize'));
                    }
                }}
            </script>
        """

    def resize(self):
        self.send({"method": "resize"})
        return


# create one single resizetrigger that will be used as a singleton everywhere
# singletons are bad but if we display multiple instances of rt for every DrawItem
# the initial offset will be impossible to manage
rt = ResizeTrigger()