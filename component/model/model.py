import datetime as dt
import warnings
from pathlib import Path

from sepal_ui import model
from sepal_ui.scripts.warning import SepalWarning
from traitlets import Bool, CInt, CUnicode, List, Unicode

import component.parameter as param
import component.scripts as cs
import modules.stackcomposed.stack_composed.stack_composed as stack


class Model(model.Model):
    # model - for process tile
    ascending = Bool().tag(sync=True)

    items = List().tag(sync=True)

    # Statistics - used for statistic tile
    selected_stat = Unicode().tag(sync=True)
    cores = CInt().tag(sync=True)
    chunks = CInt(200).tag(sync=True)
    prefix = CUnicode("New_stack").tag(sync=True)

    folders = List().tag(sync=True)
    recursive = Bool().tag(sync=True)
    date_method = Unicode(None, allow_none=True).tag(sync=True)
    start_date = Unicode(None, allow_none=True).tag(sync=True)
    end_date = Unicode(None, allow_none=True).tag(sync=True)
    selected_years = List().tag(sync=True)
    selected_months = List().tag(sync=True)

    def stack_composed(self, image_file, output_name):
        """Run stack composed algorithm."""
        stack.run(
            self.selected_stat,
            bands=1,
            output=output_name,
            num_process=self.cores,
            chunksize=self.chunks,
            inputs=image_file,
        )

    def get_inputs(self):
        """
        Return filtered images by date_method and the output composed stack name.

        Params:
            folders (list): Will use the bind folders from the statistics_tile folder
                            selector widget.
        """
        if not self.folders:
            raise Exception("You have not selected any folder to process.")

        images = list(
            set(
                [
                    str(image)
                    for folder in self.folders
                    for image in (
                        Path(folder).rglob("close*.tif")
                        if self.recursive
                        else Path(folder).glob("close*.tif")
                    )
                ]
            )
        )

        if self.date_method == "season":
            months = self.selected_months
            years = self.selected_years

            if not months and not years:
                raise Exception("Please select at least one year ")

            elif not months:
                str_yrs = [str(year) for year in years]
                warnings.warn(
                    f'No month(s) selected, executing stack for all images in {", ".join(str_yrs)}.',
                    SepalWarning,
                )
            elif not years:
                str_months = [param.MONTHS_DICT[month] for month in months]
                warnings.warn(
                    f'No year(s) selected, executing stack for all images in {", ".join(str_months)}.',
                    SepalWarning,
                )
            # Create a list with the selected months and years
            # Resample the tifs list with only the months and years
            filter_images = cs.filter_images_by_date(images, months=months, years=years)
            months = cs.re_range(months)
            years = cs.re_range(years)

            output_name = param.STACK_DIR / (
                f"{self.prefix}_Stack_{self.selected_stat}_Y{years}_m{months}.tif"
            )

        elif self.date_method == "range":
            if not self.start_date or not self.end_date:
                raise Exception("Please select a start and end date.")

            ini_date = dt.datetime.strptime(self.start_date, "%Y-%m-%d")
            end_date = dt.datetime.strptime(self.end_date, "%Y-%m-%d")

            filter_images = cs.filter_images_by_date(
                images, ini_date=ini_date, end_date=end_date
            )

            output_name = param.STACK_DIR / (
                f"{self.prefix}_Stack_{self.selected_stat}_{self.start_date}"
                f"_{self.end_date}.tif"
            )
        else:
            filter_images = images
            output_name = (
                param.STACK_DIR / f"{self.prefix}_Stack_{self.selected_stat}.tif"
            )

        if not filter_images:
            raise Exception(
                "There are no images in the selected folders/dates, please try with a"
                " different date/folder."
            )

        elif len(filter_images) == 1:
            raise Exception(
                "There is only one image in the selected range, to calculate "
                "statistics you need at least 2 images, please try a wider range."
            )

        return sorted(filter_images), output_name
