import ipyvuetify as v
import sepal_ui.sepalwidgets as sw
from sepal_ui import color
from sepal_ui.message import ms
from traitlets import Bool, link, observe

from component.scripts.resize import rt


class DrawerItem(sw.ListItem):

    """Forked sepal_ui.sepalwidgets.DrawerItem version to fix https://github.com/sepal-contrib/sepal_pysmm/issues/26."""

    rt = None
    "sw.ResizeTrigger: the trigger to resize maps and other javascript object when jumping from a tile to another"

    alert = Bool(False).tag(sync=True)
    "Bool: trait to control visibility of an alert in the drawer item"

    alert_badge = None
    "v.ListItemAction: red circle to display in the drawer"

    def __init__(
        self,
        title,
        icon=None,
        card=None,
        href=None,
        model=None,
        bind_var=None,
        **kwargs,
    ):
        # set the resizetrigger
        self.rt = rt

        icon = icon if icon else "fa-regular fa-folder"

        children = [
            v.ListItemAction(children=[v.Icon(class_="white--text", children=[icon])]),
            v.ListItemContent(
                children=[v.ListItemTitle(class_="white--text", children=[title])]
            ),
        ]

        # set default parameters
        kwargs["link"] = True
        kwargs["children"] = children
        kwargs["input_value"] = kwargs.pop("input_value", False)
        if href:
            kwargs["href"] = href  # cannot be set twice anyway
            kwargs["target"] = "_blank"
            kwargs["_metadata"] = kwargs.pop("_metadata", None)
        elif card:
            kwargs["_metadata"] = {"card_id": card}
            kwargs["href"] = kwargs.pop("href", None)
            kwargs["target"] = kwargs.pop("target", None)

        # call the constructor
        super().__init__(**kwargs)

        # cannot be set as a class member because it will be shared with all
        # the other draweritems.
        self.alert_badge = v.ListItemAction(
            children=[
                v.Icon(children=["fa-solid fa-circle"], x_small=True, color="red")
            ]
        )

        if model:
            if not bind_var:
                raise Exception(
                    "You have selected a model, you need a trait to bind with drawer."
                )

            link((model, bind_var), (self, "alert"))

    @observe("alert")
    def add_notif(self, change):
        """Add a notification alert to drawer."""
        if change["new"]:
            if self.alert_badge not in self.children:
                new_children = self.children[:]
                new_children.append(self.alert_badge)
                self.children = new_children
        else:
            self.remove_notif()

        return

    def remove_notif(self):
        """Remove notification alert."""
        if self.alert_badge in self.children:
            new_children = self.children[:]
            new_children.remove(self.alert_badge)

            self.children = new_children

        return

    def display_tile(self, tiles):
        """
        Display the apropriate tiles when the item is clicked.

        The tile to display will be all tile in the list with the mount_id as the current object.

        Args:
        ----
            tiles ([sw.Tile]) : the list of all the available tiles in the app

        Return:
        ------
            self
        """
        self.on_event("click", lambda *args: self._on_click(tiles=tiles))

        return self

    def _on_click(self, *args, tiles):
        for tile in tiles:
            if self._metadata["card_id"] == tile._metadata["mount_id"]:
                tile.show()
            else:
                tile.hide()

        # trigger the resize event
        self.rt.resize()

        # change the current item status
        self.input_value = True

        # Remove notification
        self.remove_notif()

        return self


class NavDrawer(sw.NavigationDrawer):

    """Forked sepal_ui.sepalwidgets.DrawerItem version to fix https://github.com/sepal-contrib/sepal_pysmm/issues/26."""

    items = []
    "list: the list of all the drawerItem to display in the drawer"

    def __init__(self, items=[], code=None, wiki=None, issue=None, **kwargs):
        self.items = items

        code_link = []
        if code:
            item_code = DrawerItem(
                ms.widgets.navdrawer.code, icon="fa-regular fa-file-code", href=code
            )
            code_link.append(item_code)
        if wiki:
            item_wiki = DrawerItem(
                ms.widgets.navdrawer.wiki, icon="fa-solid fa-book-open", href=wiki
            )
            code_link.append(item_wiki)
        if issue:
            item_bug = DrawerItem(
                ms.widgets.navdrawer.bug, icon="fa-solid fa-bug", href=issue
            )
            code_link.append(item_bug)

        children = [
            v.List(dense=True, children=self.items),
            v.Divider(),
            v.List(dense=True, children=code_link),
        ]

        # set default parameters
        kwargs["v_model"] = kwargs.pop("v_model", True)
        kwargs["app"] = True
        kwargs["color"] = kwargs.pop("color", color.darker)
        kwargs["children"] = children

        # call the constructor
        super().__init__(**kwargs)

        # bind the javascripts behavior
        for i in self.items:
            i.observe(self._on_item_click, "input_value")

    def display_drawer(self, toggleButton):
        """
        Bind the drawer to the app toggleButton.

        Args:
        ----
            toggleButton(v.Btn) : the button that activate the drawer
        """
        toggleButton.on_event("click", self._on_drawer_click)

        return self

    def _on_drawer_click(self, widget, event, data):
        """
        Toggle the drawer visibility.
        """
        self.v_model = not self.v_model

        return self

    def _on_item_click(self, change):
        """
        Deactivate all the other items when on of the is activated.
        """
        if change["new"] is False:
            return self

        # reset all others states
        for i in self.items:
            if i != change["owner"]:
                i.input_value = False

        return self
