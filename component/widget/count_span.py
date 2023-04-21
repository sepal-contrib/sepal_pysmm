from traitlets import Int
import sepal_ui.sepalwidgets as sw
from sepal_ui import color as sepal_color


class DownloadAlert(sw.Alert):
    def __init__(
        self, status_span, success_span, error_span, running_span, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.status_span = status_span
        self.success_span = success_span
        self.error_span = error_span
        self.running_span = running_span

        self.children = [
            self.status_span,
            self.success_span,
            self.error_span,
            self.running_span,
        ]

    def reset(self):
        self.children = [
            self.status_span,
            self.success_span,
            self.error_span,
            self.running_span,
        ]


class CountSpan(sw.Html):
    """HTML span component to control the number of images or chips that have been processed"""

    value = Int(0).tag(sync=True)
    total = Int(0).tag(sync=True)

    def __init__(self, name, color=None, with_total=True, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # make text bigger and change color to red
        self.with_total = with_total

        if color:
            color = getattr(sepal_color, color)
            self.style_ = f"color: {color};"

        self.tag = "p"
        self.name = name + ": "
        self.children = self.get_value()

    def get_value(self):
        """Get the value of the span"""

        if self.with_total:
            return [self.name, f"{self.value}/{self.total}"]
        return [self.name, f"{self.value}"]

    def update(self):
        """Update the value of the span"""
        self.value += 1
        self.children = self.get_value()

    def set_total(self, total):
        """Set the total value of the span"""
        self.total = total
        self.children = self.get_value()

    def reset(self):
        """Reset the value of the span"""
        self.value = -1
        self.total = 0
        self.update()
