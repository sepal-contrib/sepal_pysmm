import pandas as pd
import sepal_ui.scripts.utils as su
import ee
import modules.stackcomposed.stack_composed.parse as ps

__all__ = [
    'get_bounds',
    're_range',
    'filter_images_by_date',
    'images_summary',
]

@su.need_ee
def get_bounds(ee_asset, cardinal=False):
    """ Returns the min(lon,lat) and max(lon, lat) from the given asset

    Args:
        ee_asset (ee.object): GEE asset (FeatureCollection, Geometry)
        cardinal (boolean) (optional)


    Returns:
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
    return '{}-{}'.format(start, end, step)

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

        for j in range(scan+2, n-1):
            if lst[j+1] - lst[j] != step:
                result.append(formatter(lst[scan], lst[j], step))
                scan = j+1
                break
        else:
            result.append(formatter(lst[scan], lst[-1], step))
            return '_'.join(result)

    if n - scan == 1:
        result.append(str(lst[scan]))
    elif n - scan == 2:
        result.append(','.join(map(str, lst[scan:])))

    return ','.join(result)
    pd.DataFrame._repr_javascript_ = _repr_datatable_
    
def filter_images_by_date(tifs, months=None, years=None, ini_date=None, end_date=None):
    """ Return a list of images filtered by months and 
        years.
    """
    # Get a list of tuples (date, image_name)

    list_ = [(pd.Timestamp(ps.parse_other_files(image)[4]), image) for image in tifs]
    df = pd.DataFrame(list_, columns=['date','image_name']).sort_values(['date'])
    
    # Create a indexdate
    df = df.reset_index(drop=True).set_index('date')

    # If months is empty

    if years and not months:
        months = list(range(1,13))

    elif months and not years:
        years = list(set(df.index.year))

    if ini_date:
        df2 = df[ini_date:end_date]
    
    else:
        # Filter by months and years
        df2 = df[df.index.month.isin(months) & (df.index.year.isin(years))]
        
    return list(df2['image_name'])

def images_summary(tifs):

    list_ = [(pd.Timestamp(ps.parse_other_files(image)[4]), image) for image in tifs]
    df = pd.DataFrame(list_, columns=["date", "Image name"])
    df = df.sort_values(["date"])
    df = df.reset_index(drop=True).set_index("date")

    # Transform the index in string, because json can't decode
    # de datetimeindex
    df.index = df.index.strftime("%Y-%m-%d")

    return df