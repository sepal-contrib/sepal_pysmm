Soil Moisture Mapping
=====================

Part 1: Open SEPAL
------------------

1.  Open SEPAL and Login
   
    1.  If SEPAL is not already open, click the following link to open SEPAL in your browser: `<https://sepal.io/>`_
    2.  Connect SEPAL to Google account

2.  Make sure SEPAL is connected to your google account as described in the section Connecting to Google Earth Engine

    1.  Upload your area of interest (AOI) shapefile as a GEE asset

3.  Instructions for uploading a shapefile as an asset can be found here: `<https://developers.google.com/earth-engine/importing>`_

    1.  Start an :code:`m4` instance in the Terminal

Part 2: Process Sentinel-1 time series data to generate maps of soil moisture
-----------------------------------------------------------------------------

1.  Open and launch Soil Moisture Mapping application

    1.  To access the module, click on the Apps tab in SEPAL. Then use the search box and write “SOIL MOISTURE MAPPING” or use bottom pagination and find it manually.
    
    .. figure:: https://raw.githubusercontent.com/openforis/sepal_pysmm/master/doc/img/wiki/2.1.1.PNG
        :width: 500
    2.  The application will be launched and displayed over a new tab in the SEPAL panel.
    
    .. figure:: https://raw.githubusercontent.com/openforis/sepal_pysmm/master/doc/img/wiki/2.1.2.PNG
        :width: 500

    3.  The module has 5 main steps that can be selected in the left panel: "AOI selection", "download", "closing filter", "calculate statistics", and "display map".
    4.  Click over the AOI selection step and follow the next 4 sub-steps.
    5.  In the AOI selection step, choose ‘Use GEE asset’, paste your GEE Asset ID into the box and click on the “Use asset” button to select that as your AOI.
    6.  Two new select dropdowns will appear, choose your variable, field, and wait until the polygon is loaded into the map.
    
    .. figure:: https://raw.githubusercontent.com/openforis/sepal_pysmm/master/doc/img/wiki/2.1.6.PNG
        :width: 500

2.  The next step in this process is to select the date range of the data that you want to process through GEE, there are three options:
    
    1.  **Single date**: will process one soil moisture closest to the date selected
    2.  **Range**: will process all Sentinel-1 data to create a time series of soil moisture maps for the date range selected 
    3.  **All-time series**: will process all available Sentinel-1 data, since the launch of the satellite in 2015, to create a time series of soil moisture maps.

    .. figure:: https://raw.githubusercontent.com/openforis/sepal_pysmm/master/doc/img/wiki/2.2.3.PNG
        :width: 300

3.  Initiating the soil moisture processing
    
    1.  After the filters are selected, go to the “Run Process” tab. 
    2.  Once the “Start” button is clicked, the availability of Sentinel-1 data is assessed and the command is sent to Earth Engine to run the classification of soil moisture. 
    3.  This process could take a long time depending on the dimensions of the feature and on the number of images to be processed. 
    4.  If the selected dates are not available, the system will display a message with the closest images to the input dates. 
        
        1.  The most recent image available depends on the GLDAS product, which has a delay of 1 to 2 months.
    
    5.  The green Processing bar shows the name of the task that is sent to GEE. When the processing reaches 100% all the tasks have been sent to GEE and the classification of soil moisture will continue there.
    6.  After all the tasks are sent to GEE the module can be closed. The processing will continue uninterrupted in GEE. In GEE the processing can take hours or days depending on the size of the AOI and the date range selected. 

    .. figure:: https://raw.githubusercontent.com/openforis/sepal_pysmm/master/doc/img/wiki/2.3.6.PNG
        :width: 500

4.  Checking the progress of the soil moisture processing GEE
    
    1.  A way to check on the status of each task is to go to the GEE code editor.
    
    .. figure:: https://raw.githubusercontent.com/openforis/sepal_pysmm/master/doc/img/wiki/2.4.1.PNG
        :width: 500

    2.  Click on the ‘Tasks’ tab in the section on the right. You should see the process running with the spinning gear.

    .. figure:: https://raw.githubusercontent.com/openforis/sepal_pysmm/master/doc/img/wiki/2.4.2.PNG
        :width: 300

    3.  When the download completes you will see a blue checkmark. Check periodically on your download to make sure all the dates specified are being downloaded. 

Part 3: Download the soil moisture maps from GEE to SEPAL
---------------------------------------------------------

1.  Check if the processing is complete in GEE

    1.  Check on the status of each task in the GEE code editor. Click on the ‘Tasks’ tab in the section on the right. You should see blue checkmarks next to all the tasks. 
    2.  The soil moisture maps for each date have been downloaded to your Google Drive. The next step will automatically move those images from your Google account to your SEPAL account. 

    .. figure:: https://raw.githubusercontent.com/openforis/sepal_pysmm/master/doc/img/wiki/3.1.2.PNG
        :width: 300

    3.  You can start downloading the images while they are being processed in GEE, but we recommend waiting until all or part of the images has been processed in GEE.

2.  Use the download step
    
    1. In the left panel, click over the Download button. 

    .. figure:: https://raw.githubusercontent.com/openforis/sepal_pysmm/master/doc/img/wiki/3.2.1.PNG
        :width: 180

3.  Select the download task file
    
    1.  The file structure for downloading and managing the soil moisture data follows this structure: :code:`home/username/pysmm_downloads/0_raw/asset_name/row_name`
        
        1.  All downloads can always be found in the pysmm_downloads folder
        2.  Each time a different asset is used to derive soil moisture, a new folder for the asset will be created 
        3.  For each polygon that is used from the asset, selected by specifying the column and row field names, a unique folder with the row field name will contain the task download file.

        .. figure:: https://raw.githubusercontent.com/openforis/sepal_pysmm/master/doc/img/wiki/3.3.1.3.PNG
            :width: 500
 
    2.  The task download file can be found in the folder `home/user/ pysmm_downloads/0_raw/assetname/rowname/`
    3.  The task download file naming convention is: task_datedownloadinitiated_code.txt
    4.  Use the three dropdown lists to select the desired task text file is by clicking on the folder names. 
    5.  There are options to overwrite duplicates already downloaded into SEPAL and to remove the downloaded images from Google Drive. Once the images are removed from Google Drive the task download file will no longer function because those images will not be stored in Google Drive.
        
        1.  Overwrite SEPAL images: In case you previously have downloaded an image in the same path folder, the module will overwrite the images with the same name.
        2. Remove Google Drive images: Mark this option if you want to download the images to your SEPAL account and delete the files from your Google Drive account.
    
    6.  Click on the DOWNLOAD button to download the soil moisture maps from your Google Drive account to SEPAL. 
    7.  The images will download one by one, leave the application open while the download is running. 
    8.  After the data download completes you can use tools available in SEPAL to process and analyze these soil moisture maps.

Part 4: Post-process and analyze soil moisture time-series data 
---------------------------------------------------------------

After the download is complete, we can apply a robust methodology for image filtering to fill no-data gaps and assess trends in the time series of soil moisture maps. 

1.  Select the Closing filter step
    
    1. In the left panel select the “Closing filter” tab.

    .. figure:: https://raw.githubusercontent.com/openforis/sepal_pysmm/master/doc/img/wiki/4.1.1.PNG
        :width: 180

2.  Run the post-processing section of the module 
    
    1.  Navigate to the folder where the images are stored. This module will process a folder with many images, going through each of the images. Therefore, the input should be the folder in which are the raw images are stored. The module will automatically display two select menus, select the desired options.

    .. figure:: https://raw.githubusercontent.com/openforis/sepal_pysmm/master/doc/img/wiki/4.2.1.PNG
        :width: 500

    2.  The raw imagery is stored in the same folder that the task download file is located.
    3.  Click on START button to run a data-filling algorithm on each of the soil moisture maps. 
    4.  Due to speckle in the Sentinel-1 imagery the soil moisture maps contain some noise and no-data values which are corrected for to some extent using grayscale morphological operation from ORFEO toolbox, a free and open-source image processing tool. To read more about the parameterization of the Orfeo toolbox tool, read: https://www.orfeo-toolbox.org/CookBook/Applications/app_GrayScaleMorphologicalOperation.html.
    5.  This process is done by the SEPAL instance, the time will depend on the number of images and the dimension, after finishing all the images, the progress bar will be green colored. 

3.  Run the Statistics postprocess.

    1. In the left panel select the “Calculate statistics” tab.

    .. figure:: https://raw.githubusercontent.com/openforis/sepal_pysmm/master/doc/img/wiki/4.3.1.PNG
        :width: 180

    2.  After the data is filtered, a time series analysis of the soil moisture maps can be performed. Several statistics can be applied whether to the entire time series or to a specified range, statistics as median, mean, standard deviation, or linear trend (slope of the line) are available to process the selected data.  
    3.  This module uses the Stack Composed python module, which is a module that computes a specific statistic for all valid pixel values across the time series using a parallel process. 
    4.  Select column and field to process all images inside that folder.

    .. figure:: https://raw.githubusercontent.com/openforis/sepal_pysmm/master/doc/img/wiki/4.3.4.PNG
        :width: 400
 
    5.  There are three options for analyzing the data for different time frames.
    
        1.  All-time series: runs the analysis for all the images in the folder
        2.  Range:  runs the analysis for all the images within the time frame selected
        3.  Season:  the user can define a season by selecting months. The analysis is run for only the months selected within the years selected. For example, if January, February, and 2016, 2017, 2018 are selected, then the analysis would run for January 2016, January 2017, January 2018,  February 2016, February 2017, and February 2018. 
            You can also select only one year or month, so it will process all the years/months in the selection.

        4.  There are different options for the statistics that can be calculated. The options are: 
        
            1.  Median
            2.  Mean
            3.  Gmean, geometric mean
            4.  Max
            5.  Min
            6.  Std, standard deviation
            7.  Valid pixels
            8.  Linear trend
    
        5.  The ‘Valid pixels’ option will create a new image representing only the count of the valid pixels from the stack.
        6.  The Median, Mean, Geometric Mean, Max, Min, Standard Deviation and Valid pixels, are statistics that do not require much computing requirements, so the time to perform those task it’s relatively quick, depending on the extent of the image.
        7.  The advanced settings are intended to be used to improve the time and manage the system resources. Normally this is optimized automatically but can be modified by the user. This setting controls the number of processors you use for parallel processing, allowing you to optimize the time by processing a huge image by using several processors at the same time. Automatically all available processors will be used. Note that the more CPUs available in the instance you selected in the terminal, the faster the processing will be.

        .. figure:: https://raw.githubusercontent.com/openforis/sepal_pysmm/master/doc/img/wiki/4.3.5.7.PNG
            :width: 600
 
            1.  **Processors**: by default, the module will display the number of processors that are active in the current instance session and will perform the stack-composed with all of them, however, in order to test the best benchmark to the specific stack, this number could be changed within the advanced settings tab.
            2.  **Chunks**: the number in the chunk specifies the shape of the array that will be processed in parallel over the different processors. i.e., if 180 is the specified number of chunks, then the stack-composed module will divide the input image into several small square pieces of 180 pixels with its shape, for more information about how to select the best chunk shape, follow the dask documentation.
    
        8.  Once the settings are specified, click on the ‘Calculate statistics’ button.
        9.  After selecting the temporal range to run the analysis and parameter to calculate, the images that are processed are listed, along with the date of the imagery. 

        .. figure:: https://raw.githubusercontent.com/openforis/sepal_pysmm/master/doc/img/wiki/4.3.5.9.PNG
            :width: 400

        10. The processed images can be found in the folder: `home/user/pysmm_downloads/1_processed/assetname/rowname/stats`

Part 5: Visualizing imagery 
---------------------------

1.  In the left panel select the “Display map” tab.

.. figure:: https://raw.githubusercontent.com/openforis/sepal_pysmm/master/doc/img/wiki/5.1_.PNG
    :width: 180

2.  The map visualization tab will allow you to display any monoband image in your SEPAL account, not only the downloaded data.

.. figure:: https://raw.githubusercontent.com/openforis/sepal_pysmm/master/doc/img/wiki/5.2.PNG
    :width: 500

3.  Click over the “Search file” button and navigate over the dropdown list, search the desired image, and click on the “Display image” button. 

.. figure:: https://raw.githubusercontent.com/openforis/sepal_pysmm/master/doc/img/wiki/5.3.PNG
    :width: 400

4.  Wait until the image is rendered in the map and explore the general output.
5.  Mark the “Inspector” checkbox and click over any coordinate inside the image to explore the pixel values, you will see an output box in the bottom right corner with the data.

.. figure:: https://raw.githubusercontent.com/openforis/sepal_pysmm/master/doc/img/wiki/2.1.2.PNG
    :width: 500

Open-source data from Sentinel 1 operates using C-band synthetic aperture radar imaging. C-band type has a wavelength of 3.8 – 7.5 cm and thus it has limited penetration into dense forest canopies. Therefore, forested areas should be excluded from the analysis. L-band data should be used instead of such areas. 

It is recommended that densely vegetated areas are excluded from analysis due to the limitation of C-band radar to penetrate dense canopy cover. Use a forest map to exclude dense forest areas from the analysis. 
