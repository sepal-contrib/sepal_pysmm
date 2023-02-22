"""
Custom alert widget. The unique difference with the sepal_ui.sepalwidgets.Alert 
is that instead of adding thee progress bar to the end, it will be added to the
beginning of the alert.

"""

from datetime import datetime
from typing import Any, Optional

import ipyvuetify as v
import traitlets as t
from deprecated.sphinx import deprecated
from ipywidgets import Output
from sepal_ui import color
from sepal_ui.frontend.styles import TYPES
from sepal_ui.message import ms
from sepal_ui.scripts import utils as su
from sepal_ui.scripts.utils import set_type
from sepal_ui.sepalwidgets.sepalwidget import SepalWidget
from tqdm.notebook import tqdm
from traitlets import directional_link, observe
from typing_extensions import Self

__all__ = ["Divider", "Alert"]


class Divider(v.Divider, SepalWidget):

    type_: t.Unicode = t.Unicode("").tag(sync=True)
    "Added type\_ trait to specify the current color of the divider"

    def __init__(self, class_: str = "", **kwargs) -> None:
        r"""
        A custom Divider with the ability to dynamically change color.

        Whenever the type\_ trait is modified, the divider class will change accordingly.

        Args:
        ----
            class\_: the initial color of the divider
            kwargs (optional): any parameter from a v.Divider. if set, 'class\_' will be overwritten.
        """
        kwargs["class_"] = class_
        super().__init__(**kwargs)

    @observe("type_")
    def add_class_type(self, change: dict) -> Self:
        r"""
        Change the color of the divider according to the type\_.

        It is binded to the type\_ traitlet but can also be called manually.

        Args:
        ----
            change: the only useful key is 'new' which is the new required color
        """
        self.class_list.remove(*TYPES)
        self.class_list.add(change["new"])

        return self


class Alert(v.Alert, SepalWidget):

    progress_bar: Optional[tqdm] = None
    "the progress bar of the alert"

    progress_output: Optional[Output] = None
    "the output object where the progress bar is stored"

    def __init__(self, type_: str = "info", **kwargs) -> None:
        r"""
        A custom Alert widget.

        It is used as the output of all processes in the framework.
        In the voila interfaces, print statement will not be displayed.
        Instead use the sw.Alert method to provide information to the user.
        It's hidden by default.

        Args:
        ----
            type\_: The color of the Alert
            kwargs (optional): any parameter from a v.Alert. If set, 'type' will be overwritten.
        """
        # set default parameters
        kwargs.setdefault("text", True)
        kwargs["type"] = set_type(type_)
        kwargs.setdefault("class_", "mt-5")

        # call the constructor
        super().__init__(**kwargs)

        self.hide()
        self.progress_output = Output()
        # self.progress_bar = None

    def update_progress(
        self, progress: float, msg: str = "Progress", **tqdm_args
    ) -> None:
        """
        Update the Alert message with a tqdm progress bar.

        .. note::

            set the ``total`` argumentent of tqdm to use differnet values than [0, 1]

        Args:
        ----
            progress: the progress status in float
            msg: The message to use before the progress bar
            tqdm_args (optional): any arguments supported by a tqdm progress bar
        """
        # show the alert
        self.show()

        # cast the progress to float
        total = tqdm_args.get("total", 1)
        progress = float(progress)
        if not (0 <= progress <= total):
            raise ValueError(f"progress should be in [0, {total}], {progress} given")

        # Prevent adding multiple times
        if self.progress_output not in self.children:

            self.children = [self.progress_output]

            tqdm_args.setdefault("bar_format", "{l_bar}{bar}{n_fmt}/{total_fmt}")
            tqdm_args.setdefault("dynamic_ncols", False)
            tqdm_args.setdefault("total", 1)
            tqdm_args.setdefault("desc", msg)
            tqdm_args.setdefault("colour", getattr(color, self.type))

            with self.progress_output:
                self.progress_output.clear_output()
                self.progress_bar = tqdm(**tqdm_args)
                self.progress_bar.container.children[0].add_class(f"{self.type}--text")
                self.progress_bar.container.children[2].add_class(f"{self.type}--text")

                # Initialize bar
                self.progress_bar.update(0)

        self.progress_bar.update(progress - self.progress_bar.n)

        if progress == total:
            self.progress_bar.close()

        return

    def add_msg(self, msg: str, type_: str = "info") -> Self:
        r"""
        Add a message in the alert by replacing all the existing one.

        The color can also be changed dynamically.

        Args:
        ----
            msg: the message to display
            type\_: the color to use in the widget
        """
        self.show()
        self.type = set_type(type_)
        self.children = [v.Html(tag="p", children=[msg])]

        return self

    def add_live_msg(self, msg: str, type_: str = "info") -> Self:
        r"""
        Add a message in the alert by replacing all the existing one.

        Also add the timestamp of the display. The color can also be changed dynamically.

        Args:
        ----
            msg: the message to display
            type\_: the color to use in the widget
        """
        current_time = datetime.now().strftime("%Y/%m/%d, %H:%M:%S")

        self.show()
        self.type = set_type(type_)
        self.children = [
            v.Html(tag="p", children=["[{}]".format(current_time)]),
            v.Html(tag="p", children=[msg]),
        ]

        return self

    def append_msg(self, msg: str, section: bool = False, type_: str = "info") -> Self:
        r"""
        Append a message in a new parragraph, with or without divider.

        Args:
        ----
            msg: the message to display
            section: add a Divider before the added message
            type\_: the color to use in the widget
        """
        self.show()
        self.type = type_

        if len(self.children):
            current_children = self.children[:]
            if section:
                # As the list is mutable, and the trait is only triggered when
                # the children is changed, so have to create a copy.
                divider = Divider(class_="my-4", style="opacity: 0.22")

                # link Alert type with divider type
                directional_link((self, "type"), (divider, "type_"))
                current_children.extend([divider, v.Html(tag="p", children=[msg])])
                self.children = current_children

            else:
                current_children.append(v.Html(tag="p", children=[msg]))
                self.children = current_children
        else:
            self.add_msg(msg)

        return self

    def remove_last_msg(self) -> Self:
        """
        Remove the last msg printed in the Alert widget.
        """
        if len(self.children) > 1:
            current_children = self.children[:]
            self.children = current_children[:-1]
        else:
            self.reset()

        return self

    def reset(self) -> Self:
        """
        Empty the messages and hide it.
        """
        self.children = [""]
        self.hide()

        return self

    @deprecated(version="3.0", reason="This method is now part of the utils module")
    def check_input(self, input_: Any, msg: str = "") -> bool:
        r"""
        Check if the inpupt value is initialized.

        If not return false and display an error message else return True.

        Args:
            input\_: the input to check
            msg: the message to display if the input is not set

        Returns
        -------
            check if the value is initialized
        """
        msg = msg or ms.utils.check_input.error

        return su.check_input(input_, msg)
