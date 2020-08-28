#!/usr/bin/env python3

import os
import glob
import time
import pandas as pd
import subprocess

from ipywidgets import HTML
from modules.stackcomposed.stack_composed import parse as ps
from sepal_ui import sepalwidgets as s

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

def filter_dates(tifs, months=None, years=None, ini_date=None, end_date=None):
    """ Return a list of images filtered by months and 
        years.
    """
    # Get a list of tuples (date, image_name)

    list_ = [(pd.Timestamp(ps.parse_other_files(image)[4]), image) for image in tifs]
    x = pd.DataFrame(list_, columns=['date','image_name'])
    x = x.sort_values(['date'])
    
    # Create a indexdate
    x = x.reset_index(drop=True).set_index('date')

    # If months is empty

    if years and not months:
        months = list(range(1,13))

    elif months and not years:
        years = list(set(x.index.year))

    if ini_date:
        df2 = x[ini_date:end_date]
    
    else:
    # Filter by months and years
        df2 = x[x.index.month.isin(months) & (x.index.year.isin(years))]
    
    filtered = list(df2['image_name'])
    
    return filtered

def images_summary(tifs):
    
    list_ = [(pd.Timestamp(ps.parse_other_files(image)[4]), image) for image in tifs]
    x = pd.DataFrame(list_, columns=['date','Image name'])
    x = x.sort_values(['date'])
    x = x.reset_index(drop=True).set_index('date')

    # Transform the index in string, because json can't decode 
    # de datetimeindex
    x.index = x.index.strftime("%Y-%m-%d")
    
    return x

def time_message(stat, cores, chunks):
    output_msg = f'Computing {stat.lower()} using {cores} cores and {chunks} as chunk size, please wait...'
    if stat == 'linear_trend':
        lt_msg = f'\nDepending on the extent and the number of images, this process could take several minutes...'
        return "".join((output_msg, lt_msg))
    else:
        return output_msg

def stack_composed(path_selector, date_selector, statistic, alert):
    """ Start the stack composed statistics with the given parameters

    Args: 

        path_selector (PathSelector): PathSelector from sepalwidgets object.
        date_selector (DateSelector): DateSelector from sepal_ui tiles
        statistics (object io): input object to catch the parameters
        alert (s.Alert): Sepal alert object to display useful messages.
    """

    # Collect the path selector parameters
    processed_ff_path = path_selector.get_current_path()
    processed_f_path = path_selector.get_column_path()

    field = path_selector.field
    feature = path_selector.column

    # Collect the date_selector parameters

    date_method = date_selector.date_method


    season = False
    range_ = False

    if date_method == 'Season':
        season = True

    elif date_method == 'Range':
        range_ = True
        ini_date = date_selector.start_date
        end_date = date_selector.end_date


    # Collect statistics and advanced settings
    selected_stat = statistic.get_stat_as_parameter()
    cores = str(statistic.cores)
    chunks = str(statistic.chunks)


    processed_stat_path = os.path.join(processed_ff_path, 'stats')
    if not os.path.exists(processed_stat_path):
         os.makedirs(processed_stat_path)

    # Create a list from all the images 
    tifs = glob.glob(f'{processed_ff_path}/close*.tif')
    # tifs = glob.glob(f'{processed_f_path}/*/close*.tif') # To compute all the folders
    if not tifs:
        alert.add_msg(f'There are no images for the selected dates, \
            please try with a different range.', type_='error')

        return


    if season:

        # Parse the selected months to numbers
        months = date_selector.months_to_numbers()
        years = date_selector.selected_years

        if not months and not years:
            alert.add_msg(f'Error: Please select at least one year', type_='error')
            return

        elif not months:
            alert.add_msg(f'No month(s) selected, executing stack for \
                all images in {", ".join(str(year) for year in years)}.', type_='info')

        elif not years:
            alert.add_msg(f'No year(s) selected, executing stack for \
                all images in {", ".join(date_selector.selected_months)}.', type_='info')

        # Create a list with the selected months and years
        # Resample the tifs list with only the months and years
        tifs = filter_dates(tifs, months=months, years=years)
        months = re_range(months)
        years = re_range(years)


        processed_stat_name = os.path.join(processed_stat_path, 
                           f'Stack_{selected_stat.upper()}_{feature}_{field}_Y{years}_m{months}.tif')

    elif range_:
        
        tifs = filter_dates(tifs, ini_date=ini_date, end_date=end_date)
        start = ini_date.strftime("%Y-%m-%d")
        end = end_date.strftime("%Y-%m-%d")
        processed_stat_name = os.path.join(processed_stat_path, 
                                           f'Stack_{selected_stat.upper()}_{feature}_{field}_{start}_{end}.tif')

    else:
        
        processed_stat_name = os.path.join(processed_stat_path, 
                                       f'Stack_{selected_stat.upper()}_{feature}_{field}.tif')

    alert.add_msg(f'Executing {selected_stat} for {len(tifs)} images...', type_='info')
    # Create a file with the selected images
    tmp_tif_file = [os.path.join(processed_stat_path, 'tmp_images.txt')]

    tifs = sorted(tifs)
    with open(tmp_tif_file[0], 'w') as f:
        f.write('\n'.join(tifs))

    summary = images_summary(tifs)

    vdf = s.VueDataFrame(data=summary, title='Selected Images')
    display(vdf)

    print(time_message(selected_stat, cores, chunks))
    tic = time.perf_counter()


    process = subprocess.run(['python3', 
                                f'{os.getcwd()}/modules/stackcomposed/bin/stack-composed',
                                '-stat', selected_stat,
                                '-bands', '1',
                                '-p', cores,
                                '-chunks', chunks,
                                '-o', processed_stat_name]+
                                 tmp_tif_file,

                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            universal_newlines=True)

    # Once the process has ran remove the tmp_tif_file
    os.remove(tmp_tif_file[0])
                             
    if process.returncode == 0:
        toc = time.perf_counter()
        elapsed_time = round(toc-tic, 2)
        alert.add_msg(f'Done in {elapsed_time} seconds!', type_='success')
        link = f"https://sepal.io/api/sandbox/jupyter/tree/pysmm_downloads/1_processed/{feature}/{field}/stats"
        html_link = f'<br>The processed images can be found in <a href = "{link}" target="_blank"> {processed_ff_path}</a>'
        display(HTML(html_link))
    else:
        alert.add_msg(process.stderr, type_='error')