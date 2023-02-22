import json
from pathlib import Path

import ipyvuetify as v
import sepal_ui.scripts.utils as su
import sepal_ui.sepalwidgets as sw
from natsort import humansorted
from sepal_ui.frontend import styles as ss
from traitlets import Bool, List, link, observe

__all__ = ["FolderSelector", "FolderSelectorView"]


class FolderSelectorView(v.Card):
    """
    Folder selector view.
    
    Contains the option to search the files ending with the
    given wildcard with the recursive option. It will display the lenght of the found
    items in an alert header.

    Args:
    ----
        wildcard (str): pattern to find files within the selected folders.
        ** FolderSelector args.

    """

    def __init__(
        self,
        folder="/",
        max_depth=None,
        max_selection=None,
        wildcard="*",
        *args,
        **kwargs,
    ):
        self.style_ = "overflow-x:hidden;"
        super().__init__(*args, **kwargs)

        self.wildcard = wildcard

        self.alert_info = sw.Alert(
            children=["Please select a folder with .tif images"]
        ).show()
        self.w_selector = FolderSelector(folder, max_depth, max_selection)
        self.w_recursive = v.Switch(label="Search recursively", v_model=False)

        self.children = [
            v.CardTitle(children=["Select a folder", v.Divider(), self.w_recursive]),
            self.alert_info,
            self.w_selector,
        ]

        self.w_selector.observe(self.get_image_number, "v_model")
        self.w_recursive.observe(lambda *args: self.w_selector.reset(), "v_model")

    @su.switch("loading", "disabled", on_widgets=["w_selector"])
    def get_image_number(self, change):
        """Get the number of images in the current path list."""
        if change["new"]:
            if not self.w_recursive.v_model:
                number_of_images = sum(
                    [
                        len(list(Path(folder).glob(self.wildcard)))
                        for folder in change["new"]
                    ]
                )
            else:
                number_of_images = sum(
                    [
                        len(list(Path(folder).rglob(self.wildcard)))
                        for folder in change["new"]
                    ]
                )
            self.alert_info.add_msg(
                f"There are {number_of_images} images in the selected folder(s)."
            )
        else:
            self.alert_info.add_msg("Please select a folder with images to process.")


class FolderSelector(v.List):
    """
    Multiple folder selector widget.

    Args:
    ----
        folder (str, Path) (optional): Initial folder. Default : '/'
        max_depth (int): maximum depth levels allowed from the initial folder.
        max_selection (int): set the maximum number of elements that can be selected.

    Params:
        max_depth (int): Maximum levels of depth that can be accessed.
        base_folder (Path): base folder, given from the folder arg.
        max_depth_folder (Path): Maximum depth folder. Given by max_depth arg.
        current_folder (Path): Folder in the current state of the widget.
        folders (list): Folders in the current folder.
        max_selection (int): Maximum nunmber of folders that can be selected

        Traits:
            v_model: Will store the selected elements.
            loading (bool): Whether the Folder Selector is loading or not.

    """

    v_model = List().tag(sync=True)
    loading = Bool().tag(sync=True)

    def __init__(self, folder="/", max_depth=None, max_selection=None, *args, **kwargs):
        p_style = json.loads((ss.JSON_DIR / "progress_bar.json").read_text())

        self.style_ = "overflow-x:none"
        self.folders = None
        self.max_depth = max_depth
        self.max_selection = max_selection
        self.base_folder = Path("/") if not folder else Path(folder)

        if self.max_depth is not None:
            if self.max_depth > len(self.base_folder.parents):
                raise Exception(
                    f"The folder {self.base_folder} only has a {len(self.base_folder.parents)} "
                    f"depth. You've selected {self.max_depth} as max depth."
                )

            self.max_depth_folder = (
                self.base_folder
                if max_depth == 0
                else self.base_folder.parents[max_depth - 1]
            )

        # Give an initial value. It will change over each change.
        self.current_folder = self.base_folder

        self.style_ = "overflow: auto; border-radius: 0 0 0 0;overflow-x:none"
        self.max_height = "340px"
        self.min_height = "300px"

        super().__init__(*args, **kwargs)

        self.w_loading = v.ProgressLinear(
            indeterminate=False,
            background_color="grey darken-3",
            color=p_style["color"][v.theme.dark],
        )

        self.item_group = ListItemGroup(
            max_selection=self.max_selection,
            children=self.get_folder_group(self.current_folder),
        )

        self.children = [self.w_loading, self.item_group]

        self.item_group.observe(self.on_folder, "v_model")

        link((self.item_group, "selected"), (self, "v_model"))
        link((self.w_loading, "indeterminate"), (self, "loading"))

    def get_folder_group(self, path):
        """
        Get the folders in the given path. 
        
        Will be stored in folders class variable.
        """
        folders = humansorted(
            [str(folder) for folder in Path(path).glob("[!.]*/") if folder.is_dir()]
        )

        self.folders = [str(Path(path).parent), *folders]

        # Enumerate items. We will be able to know which one is the parent
        return [
            ListItem(value=folder, position=i) for i, folder in enumerate(self.folders)
        ]

    @su.switch("loading")
    def on_folder(self, change):
        if change["new"] is not None:
            # Check if we can access to this path or if it's restricted by depth
            restricted = (
                Path(self.folders[change["new"]]) == self.max_depth_folder.parent
                if self.max_depth is not None
                else False
            )

            if not restricted:
                self.current_folder = Path(self.folders[change["new"]])
                items = self.get_folder_group(self.current_folder)
                self.item_group.children = items
                self.item_group.v_model = None

    def reset(self):
        """Clear current selected elements."""
        self.item_group.reset()


class ListItem(v.Flex):
    """Custom ListItem that will store a checkbox."""

    # Workaround: It has to be a container: using directly a ListItem
    # will cause that the checkbox is inside the ListItem,
    # So, the item will be selected when the checkbox is checked.

    is_selected = Bool().tag(sync=True)

    def __init__(self, value, position, multiple=True, *args, **kwargs):
        self.value = value
        self.class_ = "d-flex"
        self.position = position

        value = Path(value)

        super().__init__(*args, **kwargs)

        self.w_selected = v.Checkbox(v_model=False)

        ICON_TYPES = json.loads((ss.JSON_DIR / "file_icons.json").read_text())

        if position == 0:
            icon = ICON_TYPES["PARENT"]["icon"]
            color = ICON_TYPES["PARENT"]["color"][v.theme.dark]
        elif value.suffix in ICON_TYPES.keys():
            icon = ICON_TYPES[value.suffix]["icon"]
            color = ICON_TYPES[value.suffix]["color"][v.theme.dark]
        else:
            icon = ICON_TYPES["DEFAULT"]["icon"]
            color = ICON_TYPES["DEFAULT"]["color"][v.theme.dark]
        self.item = v.ListItem(
            children=[
                v.ListItemAction(children=[v.Icon(color=color, children=[icon])]),
                v.ListItemContent(
                    children=[
                        v.ListItemTitle(
                            children=[
                                str(f"../{value.stem}")
                                if position == 0
                                else str(value.stem)
                            ]
                        ),
                    ]
                ),
            ]
        )

        self.children = [self.item] if position == 0 else [self.item, self.w_selected]

        if multiple:
            self.w_selected.disabled = False

        link((self.w_selected, "v_model"), (self, "is_selected"))


class ListItemGroup(v.ListItemGroup):
    selected = List([]).tag(sync=None)

    def __init__(self, children, max_selection=None, *args, **kwargs):
        self.v_model = None
        self.max_selection = max_selection
        self.last_checked = 0

        super().__init__(*args, **kwargs)

        self.children = children

    @observe("children")
    def update_observe(self, change):
        """Update widget observation once the childrens have changed."""
        # Reset previous selected items
        self.selected = []

        # Observe each children with the selected trait
        _ = [item.observe(self.set_selected, "is_selected") for item in self.children]

    def set_selected(self, change):
        """Bind every item with the selected trait if it's checkbox is checkd."""
        # Create an index to store the last selection.
        # Will be used to un-select an element when the max_selection is given
        self.last_checked += 1
        change["owner"].last_checked = self.last_checked

        self.selected_widgets = sorted(
            [chld for chld in self.children if chld.is_selected],
            key=lambda x: x.last_checked,
        )

        self.selected = [chld.value for chld in self.selected_widgets]

        # Deselect the first selected if there's a selected one>max_selection
        if self.max_selection is not None:
            if len(self.selected_widgets) > self.max_selection:
                self.selected_widgets[0].w_selected.v_model = False

    def reset(self):
        """Clear selected elements."""
        [setattr(chld, "is_selected", False) for chld in self.children]
