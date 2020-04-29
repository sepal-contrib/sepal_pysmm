# How to use

This is a mini guide step by step for use the StackComposed

## Recommendation for data input

There are some recommendation for the data input for process, all input images need:

- To be in the same projection
- Have the same pixel size
- Have pixel registration

For the moment, the image formats support are: `tif`, `img` and `ENVI` (hdr)

## Usage

`StackComposed` takes some command-line options:

```bash
stack-composed -stat STAT -bands BANDS [-p P] [-chunks CHUNKS] [-start DATE] [-end DATE] [-o OUTPUT] [-ot dtype] inputs
```

- `-stat` STAT (required)
    - statistic for compute the composed along the time axis ignoring any nans, this is, compute the statistic along the time series by pixel (see [about](about.md))
    - statistics options:
        - `median`: compute the median

        - `mean`: compute the arithmetic mean

        - `gmean`: compute the geometric mean, that is the n-th root of (x1 * x2 * ... * xn)

        - `max`: compute the maximum value

        - `min`: compute the minimum value

        - `std`: compute the standard deviation

        - `valid_pixels`: compute the count of valid pixels

        - `last_pixel`: return the last _valid_ pixel base on the date of the raster image, required filename as metadata [\[2\]](#extra-metadata)

        - `jday_last_pixel`: return the julian day of the _last valid pixel_ base on the date of the raster image, required filename as metadata [\[2\]](#extra-metadata)

        - `jday_median`: return the julian day of the median value base on the date of the raster image, required filename as metadata [\[2\]](#extra-metadata)

        - `percentile_nn`: compute the percentile nn, for example, for percentile 25 put "percentile_25" (must be in the range 0-100)

        - `trim_mean_LL_UL`: compute the truncated mean, first clean the time pixels series below to percentile LL (lower limit) and above the percentile UL (upper limit) then compute the mean, e.g. trim_mean_25_80. This statistic is not good for few time series data

        - `linear_trend`: compute the linear trend (slope of the line) using least-squares method of the valid pixels time series ordered by the date of images. The output by default is multiply by 1000 in signed integer. required filename as metadata [\[2\]](#extra-metadata)

    - example: -stat median

- `-bands` BANDS (required)
    - band or bands to process
    - input: integer or integers comma separated
    - example: -bands 1,2,4

- `-nodata` NODATA (optional)
    - input pixel value to treat as nodata
    - input: integer, float or string
    - example: -nodata 0 (or: "<0", ">=0", "<0 or >1", ">=0 or <=1")

- `-p` P (optional)
    - number of process
    - input: integer
    - by default: total cores - 1
    - example: -p 10

- `-chunks` CHUNKS (optional)
    - chunks size for parallel process [\[1\]](#chunks-sizes)
    - input: integer
    - by default: 1000
    - example: -chunks 800

- `-o` OUTPUT (optional)
    - output directory and/or filename for save results
    - input: string, absolute or relative path or filename
    - by default: save in the same directory of run with a standard name
    - example: -o /dir/to/file.tif

- `-ot` DTYPE (optional)
    - output data type for results
    - options: byte, uint16, uint32, int16, int32, float32, float64
    - example: -ot float64

- `-start` DATE (optional)
    - filter the images with the start date DATE, can be used alone or in combination with -end argument, required filename as metadata [\[2\]](#extra-metadata)
    - format: YYYY-MM-DD
    - example: -start 2016-06-01

- `-end` DATE (optional)
    - filter the images with the end date DATE, can be used alone or in combination with -start argument, required filename as metadata [\[2\]](#extra-metadata)
    - format: YYYY-MM-DD
    - example: -end 2016-12-31

- `inputs` (required)
    - directories or images files to process
    - input: filenames and/or absolute or relative directories
    - example: /dir1 /dir2 *.tif

### Chunks sizes

Choosing good values for chunks can strongly impact performance. StackComposed only required a ram memory enough only for the sizes and the number of chunks that are currently being processed in parallel, therefore the chunks sizes going together with the number of process. Here are some general guidelines. The strongest guide is memory:

- The size of your blocks should fit in memory.

- Actually, several blocks should fit in memory at once, assuming you want multi-core

- The size of the blocks should be large enough to hide scheduling overhead, which is a couple of milliseconds per task

### Filename as metadata

Some statistics or arguments required extra information for each image to process. The StackComposed acquires this extra metadata using parsing of the filename. Currently support two format:

* **Official Landsat filenames:**
    * Example:
        * LE70080532002152EDC00...tif
        * LC08_L1TP_007059_20161115...tif


* **SMByC format:**
    * Example:
        * Landsat_8_53_020601_7ETM...tif

For them extract: landsat version, sensor, path, row, date and julian day.