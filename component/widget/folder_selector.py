import ipyvuetify as v
from traitlets import Bool, link, List, observe, dlink
from pathlib import Path
from natsort import humansorted
import sepal_ui.scripts.utils as su
from sepal_ui.frontend.styles import *

__all__ = ["FolderSelector"]


class FolderSelector(v.List):
    """ Multiple folder selector widget
    
    Args:
        folder (str, Path) (optional): Initial folder. Default : '/'
    
    Params:
        v_model: Will store the selected elements.
        loading (bool): Whether the Folder Selector is loading or not.
        
    """
    v_model = List().tag(sync=True)
    loading = Bool().tag(sync=True)
    
    def __init__(self, folder='/', *args, **kwargs):

        self.folders = None
        self.style_="overflow: auto; border-radius: 0 0 0 0;overflow-y:none"
        self.max_height="340px"
        self.min_height="300px"

        super().__init__(*args, **kwargs)

        self.w_loading = v.ProgressLinear(
            indeterminate=False,
            background_color="grey darken-3",
            color=COMPONENTS["PROGRESS_BAR"]["color"],
        )
        
        self.item_group = ListItemGroup(children=self.get_folder_group(folder))
        
        self.children = [self.w_loading, self.item_group]

        
        self.item_group.observe(self.on_folder, "v_model")
        
        link((self.item_group, 'selected'), (self, 'v_model'))
        link((self.w_loading, 'indeterminate'), (self, 'loading'))

    def get_folder_group(self, path):
        """Get the folders in the current patn. Will be stored in folders class 
        variable.
        
        """

        folders = humansorted(
            [
                str(folder)
                for folder in Path(path).glob("[!.]*/")
                if folder.is_dir()
            ]
        )
        self.folders = [str(Path(path).parent)] + folders
        
        # Enumerate items. We will be able to know which one is the parent
        return [
            ListItem(value=folder, position=i)
            for i, folder in enumerate(self.folders)
        ]
        
    @su.switch("loading")
    def on_folder(self, change):

        if change["new"] is not None:
            items = self.get_folder_group(self.folders[change["new"]])
            self.item_group.children = items
            self.item_group.v_model = None


class ListItem(v.Flex):
    """Custom ListItem that will store a checkbox"""

    # Workaround: It has to be a container: using directly a ListItem
    # will cause that the checkbox is inside the ListItem,
    # So, the item will be selected when the checkbox is checked.

    is_selected = Bool().tag(sync=True)

    def __init__(self, value, position, multiple=True, *args, **kwargs):

        self.value = value
        self.class_ = "d-flex"
        value = Path(value)

        super().__init__(*args, **kwargs)

        selected = v.Checkbox(v_model=False)

        if position == 0:
            icon = ICON_TYPES["PARENT"]["icon"]
            color = ICON_TYPES["PARENT"]["color"]
        elif value.suffix in ICON_TYPES.keys():
            icon = ICON_TYPES[value.suffix]["icon"]
            color = ICON_TYPES[value.suffix]["color"]
        else:
            icon = ICON_TYPES["DEFAULT"]["icon"]
            color = ICON_TYPES["DEFAULT"]["color"]
            
        self.item = v.ListItem(
            children=[
                v.ListItemAction(children=[v.Icon(color=color, children=[icon])]),
                v.ListItemContent(
                    children=[
                        v.ListItemTitle(children=[
                            str(f"../{value.stem}") if position==0 else str(value.stem)
                        ]),
                    ]
                ),
            ]
        )

        self.children = [self.item] if position==0 else [self.item, selected]
            
        if multiple:
            selected.disabled = False
            
        link((selected, "v_model"), (self, "is_selected"))

class ListItemGroup(v.ListItemGroup):

    selected = List([]).tag(sync=None)

    def __init__(self, children, *args, **kwargs):

        self.v_model = None

        super().__init__(*args, **kwargs)

        self.children = children
        
    @observe('children')
    def update_observe(self, change):
        """Update widget observes once the childrens has changed"""
        # Reset previous selected items
        self.selected = []
        
        # Observe each children with the selected trait
        _ = [
            item.observe(self.set_selected, "is_selected") 
            for item
            in self.children
        ]

    def set_selected(self, change):
        """Bind every item with the selected trait if it's checkbox is checkd"""
        
        self.selected = [
            (chld.value) for chld in self.children if chld.is_selected
        ]
