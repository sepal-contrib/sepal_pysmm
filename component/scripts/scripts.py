import ee
import pandas as pd
import sepal_ui.scripts.utils as su

import modules.stackcomposed.stack_composed.parse as ps

__all__ = [
    "get_bounds",
    "re_range",
    "filter_images_by_date",
    "images_summary",
]


@su.need_ee
def get_bounds(ee_asset, cardinal=False):
    """
    Return the min(lon,lat) and max(lon, lat) from the given asset.

    Args:
        ee_asset (ee.object): GEE asset (FeatureCollection, Geometry)
        cardinal (boolean) (optional)


    Returns
    -------
        If cardinal True: returns cardinal points tl, bl, tr, br
        If cardinal False: returns bounding box
    """
    #
    ee_bounds = ee.FeatureCollection(ee_asset).geometry().bounds().coordinates()
    coords = ee_bounds.get(0).getInfo()
    ll, ur = coords[0], coords[2]

    # Get the bounding box
    min_lon, min_lat, max_lon, max_lat = ll[0], ll[1], ur[0], ur[1]

    # Get (x, y) of the 4 cardinal points
    tl = (min_lon, max_lat)
    bl = (min_lon, min_lat)
    tr = (max_lon, max_lat)
    br = (max_lon, min_lat)

    if cardinal:
        return tl, bl, tr, br

    return min_lon, min_lat, max_lon, max_lat


def formatter(start, end, step):
    return "{}-{}".format(start, end, step)


def re_range(lst):
    n = len(lst)
    result = []
    scan = 0
    while n - scan > 2:
        step = lst[scan + 1] - lst[scan]
        if lst[scan + 2] - lst[scan + 1] != step:
            result.append(str(lst[scan]))
            scan += 1
            continue

        for j in range(scan + 2, n - 1):
            if lst[j + 1] - lst[j] != step:
                result.append(formatter(lst[scan], lst[j], step))
                scan = j + 1
                break
        else:
            result.append(formatter(lst[scan], lst[-1], step))
            return "_".join(result)

    if n - scan == 1:
        result.append(str(lst[scan]))
    elif n - scan == 2:
        result.append(",".join(map(str, lst[scan:])))

    return ",".join(result)
    pd.DataFrame._repr_javascript_ = _repr_datatable_  # noqa


def filter_images_by_date(tifs, months=None, years=None, ini_date=None, end_date=None):
    """Return a list of images filtered by months and years."""
    # Get a list of tuples (date, image_name)

    list_ = [(pd.Timestamp(ps.parse_other_files(image)[4]), image) for image in tifs]
    df = pd.DataFrame(list_, columns=["date", "image_name"]).sort_values(["date"])

    # Create a indexdate
    df = df.reset_index(drop=True).set_index("date")

    # If months is empty

    if years and not months:
        months = list(range(1, 13))

    elif months and not years:
        years = list(set(df.index.year))

    if ini_date:
        df2 = df[ini_date:end_date]

    else:
        # Filter by months and years
        df2 = df[df.index.month.isin(months) & (df.index.year.isin(years))]

    return list(df2["image_name"])


def images_summary(tifs):
    list_ = [(pd.Timestamp(ps.parse_other_files(image)[4]), image) for image in tifs]
    df = pd.DataFrame(list_, columns=["date", "Image name"])
    df = df.sort_values(["date"])
    df = df.reset_index(drop=True).set_index("date")

    # Transform the index in string, because json can't decode
    # de datetimeindex
    df.index = df.index.strftime("%Y-%m-%d")

    return df


import ee

# Initialize the Earth Engine API
ee.Initialize()


def get_geogrid_bounds(geometry, cell_size_deg):
    """Creates a list of bounds for each of the tiles based on the cell_size"""

    def add_bounds_properties(feature):
        """adds a bounds property to each feature."""
        bounds = feature.geometry().bounds()
        coords = ee.List(bounds.coordinates().get(0))
        ll = ee.List(coords.get(0))
        ur = ee.List(coords.get(2))

        return feature.set({"bounds": [ll.get(0), ll.get(1), ur.get(0), ur.get(1)]})

    def make_row(y):
        """creates the fishnet grid"""
        y = ee.Number(y).multiply(cell_size_deg).add(ll.get(1))

        def make_rect(x):
            x = ee.Number(x).multiply(cell_size_deg).add(ll.get(0))
            coords = ee.List([x, y, x.add(cell_size_deg), y.add(cell_size_deg)])
            return ee.Feature(ee.Geometry.Rectangle(coords))

        return x_list.map(make_rect)

    # Get the bounding box of the geometry
    bounds = geometry.bounds()
    coords = ee.List(bounds.coordinates().get(0))
    ll = ee.List(coords.get(0))
    ur = ee.List(coords.get(2))

    # Calculate the number of grid cells in x and y directions
    x_cells = ee.Number(ur.get(0)).subtract(ll.get(0)).divide(cell_size_deg).ceil()
    y_cells = ee.Number(ur.get(1)).subtract(ll.get(1)).divide(cell_size_deg).ceil()

    # Check if the AOI is smaller than the grid size
    if x_cells.getInfo() == 0 or y_cells.getInfo() == 0:
        geom_with_bounds = geometry.map(add_bounds_properties)
        return geom_with_bounds.aggregate_array("bounds").getInfo()

    # Create lists with start and end coordinates in x and y directions
    x_list = ee.List.sequence(0, x_cells, 1)
    y_list = ee.List.sequence(0, y_cells, 1)

    # Get the grid
    grid = ee.FeatureCollection(y_list.map(make_row).flatten())

    # Filter out geometries that are not overlapping the area of interest
    intersected_grid = grid.map(lambda f: ee.Feature(f.intersection(geometry)))

    # Add an 'area' property to each feature so we can filter out the ones that doesn't have any
    intersected_grid = intersected_grid.map(
        lambda f: f.set("area", f.geometry().area())
    )
    intersected_grid = intersected_grid.filter(ee.Filter.gt("area", 0))

    # Add minlon, minlat, maxlon, and maxlat properties to each feature
    intersected_grid_with_bounds = intersected_grid.map(add_bounds_properties)
    chip_bounds = intersected_grid_with_bounds.aggregate_array("bounds").getInfo()

    return chip_bounds
