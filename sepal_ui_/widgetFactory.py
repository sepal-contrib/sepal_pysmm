from datetime import datetime
import traitlets
import os

import ipyvuetify as v

#######
from . import widgetBinding as wb
from . import sepalwidgets as s
from . import mapping
from .utilities import utils
from .styles.styles import *

from haversine import haversine

import ee

ee.Initialize()


# create a app bar
def AppBar(title="SEPAL module"):
    """
    create an appBar widget with the provided title using the sepal color framework

    Returns:
        app (v.AppBar) : The created appbar
        toolbarButton (v.Btn) : The button to display the side drawer
    """

    toolBarButton = v.Btn(
        icon=True,
        children=[v.Icon(class_="white--text", children=["mdi-dots-vertical"])],
    )

    appBar = v.AppBar(
        color=sepal_main,
        class_="white--text",
        dense=True,
        app=True,
        children=[
            toolBarButton,
            v.ToolbarTitle(children=[title]),
        ],
    )

    return (appBar, toolBarButton)


# create a drawer_item
def DrawerItem(title, icon=None, card="", href=""):
    """
    create a drawer item using the user input

    Args:
        title (str): the title to display in the drawer,
        icon (str, optional): the icon id following the mdi code. folder icon if None
        card (str), optional): the tile metadata linked to the drawer
        href(str, optional): the link targeted by the button

    Returns:
        item (v.ListItem): the item to display
    """

    if not icon:
        icon = "mdi-folder-outline"

    item = v.ListItem(
        link=True,
        children=[
            v.ListItemAction(children=[v.Icon(class_="white--text", children=[icon])]),
            v.ListItemContent(
                children=[v.ListItemTitle(class_="white--text", children=[title])]
            ),
        ],
    )

    if not href == "":
        item.href = href
        item.target = "_blank"

    if not card == "":
        item._metadata = {"card_id": card}

    return item


# create a drawer
def NavDrawer(items, code=False, wiki=False, issue=None):
    """
    create a navdrawer using the different items of the user and the sepal color framework. The drawer always include links to the github page of the project for wiki, bugs and repository.

    Args:
        items ([v.ListItem]) : the list of the list item the user wants to add to the nav drawer
        code (str, optionnal) : the absolute link to the github code. not display if None
        wiki (str, optionnal) : the absolute link to the github wiki. not display if None
        issue (str, optionnal) : the absolute link to the github issues. not display if None

    Returns:
        navDrawer (v.NavigationDrawer) : the nav drawer of the web page
    """

    code_link = []
    if code:
        item_code = DrawerItem("Source code", icon="mdi-file-code", href=code)
        code_link.append(item_code)
    if wiki:
        item_wiki = DrawerItem("Wiki", icon="mdi-book-open-page-variant", href=wiki)
        code_link.append(item_wiki)
    if issue:
        item_bug = DrawerItem("Bug report", icon="mdi-bug", href=issue)
        code_link.append(item_bug)

    navDrawer = v.NavigationDrawer(
        v_model=True,
        app=True,
        color=sepal_darker,
        children=[
            v.List(dense=True, children=items),
            v.Divider(),
            v.List(dense=True, children=code_link),
        ],
    )

    return navDrawer


# create a footer
def Footer(text="SEPAL \u00A9 2020"):
    """
    create a footer with cuzomizable text. Not yet capable of displaying logos

    Returns:
        footer (v.Footer) : an app footer
    """

    footer = v.Footer(color=sepal_main, class_="white--text", app=True, children=[text])

    return footer


# create an app
def App(tiles=[""], appBar=None, footer=None, navDrawer=None):
    """
    Create an app display with the tiles created by the user. Display false footer and appBar if not filled. navdrawer is fully optionnal

    Args:
        tiles ([v.Layout]) : the list of tiles the user want to display in step order.
        appBar (v.appBar, optionnal) : the custom appBar of the module
        footer (v.Footer, optionnal) : the custom footer of the module
        navDrawer (v.NavigationDrawer, optional) : the navigation drawer to allow the display of specific tiles

    Returns:
        app (v.App) : the complete app to display
        toolBarButton (v.Btn) : the created toolbarButton, None if the appBar was already existing
    """

    app = v.App(v_model=None)
    app_children = []

    # add the navDrawer if existing
    if navDrawer:
        app_children.append(navDrawer)

    # create a false appBar if necessary
    toolBarButton = None
    if not appBar:
        appBar, toolBarButton = AppBar()
    app_children.append(appBar)

    # add the content of the app
    content = v.Content(children=[v.Container(fluid=True, children=tiles)])
    app_children.append(content)

    app.children = app_children

    return (app, toolBarButton)


# create a tile
def Tile(id_, title, inputs=[""], btn=None, output=None):
    """
    create a customizable tile for the sepal UI framework

    Args:
        id_ (str) : the Id you want to gave to the tile. This Id will be used by the draweritems to show and hide the tile.
        title (str) : the title that will be display on the top of the tile
        btn (v.Btn, optionnal) : if the tile launch a py process, attached a btn to it.
        output( v.Alert, optional) : if you want to display text results of your process add an alert widget to it

    Returns:
        tile (v.Layout) : a fully functionnal tile to be display in an app
    """

    if btn:
        inputs.append(btn)

    if output:
        inputs.append(output)

    inputs_widget = v.Layout(
        _metadata={"mount-id": "{}-data-input".format(id_)},
        row=True,
        class_="pa-5",
        align_center=True,
        children=[v.Flex(xs12=True, children=[widget]) for widget in inputs],
    )

    tile = v.Layout(
        _metadata={"mount_id": id_},
        row=True,
        xs12=True,
        align_center=True,
        class_="ma-5 d-inline",
        children=[
            v.Card(
                class_="pa-5",
                raised=True,
                xs12=True,
                children=[
                    v.Html(xs12=True, tag="h2", children=[title]),
                    v.Flex(xs12=True, children=[inputs_widget]),
                ],
            )
        ],
    )

    return tile


# create downloadable links button
def DownloadBtn(text, path="#"):
    btn = v.Btn(
        class_="ma-2",
        xs5=True,
        color="success",
        href=utils.create_download_link(path),
        children=[v.Icon(left=True, children=["mdi-download"]), text],
    )

    return btn


# create a process button
def ProcessBtn(text="Launch process"):
    """
    create a process button filled with the provided text

    Returns:
        btn (v.Btn) : the btn
    """
    btn = v.Btn(
        color="primary",
        children=[v.Icon(left=True, children=["mdi-map-marker-check"]), text],
    )

    return btn


# hide all the cards but one for the start of the notebook
def hideCards(tileId, tiles):
    """
    hide all the cards but the on selected

    Args:
        tileId (str) : the card to be display when opening the app
        tiles ([v.cards]) : a list of the cards in the app
    """
    for tile in tiles:
        if tileId == tile._metadata["mount_id"]:
            tile.class_ = "ma-5 d-inline"
        else:
            tile.class_ = "ma-5 d-none"
