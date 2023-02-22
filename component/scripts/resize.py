import ipyvuetify as v
from traitlets import default


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
