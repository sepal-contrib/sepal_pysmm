from pathlib import Path
from traitlets import Bool, Unicode, List, Int, CUnicode
from sepal_ui import model
from sepal_ui.scripts.warning import SepalWarning
import warnings
import subprocess
import component.parameter as param

class Model(model.Model):

    # If changed, propagate the status to all the tiles that are listening.
    rmdrive = Bool(False).tag(sync=True)
    overwrite = Bool(False).tag(sync=True)

    items = List().tag(sync=True)
    
    # Statistics
    selected_stat = Unicode().tag(sync=True)
    cores = CUnicode().tag(sync=True)
    chunks = CUnicode(200).tag(sync=True)
    prefix = CUnicode('New_stack').tag(sync=True)
    
    folders = List().tag(sync=True)
    recursive = Bool().tag(sync=True)
    date_method = Unicode(None, allow_none=True).tag(sync=True)
    start_date = Unicode(None, allow_none=True).tag(sync=True)
    end_date = Unicode(None, allow_none=True).tag(sync=True)
    selected_years = List().tag(sync=True)
    selected_months = List().tag(sync=True)
        
    def get_inputs(self):
        """Return filtered images by date_method and the output composed stack name"""
        
        if self.recursive:
            images = list(set([
                str(image) for folder in self.folders for image in Path(folder).rglob('close*.tif')
            ]))
        else:
            images = list(set([
                str(image) for folder in self.folders for image in Path(folder).glob('close*.tif')
            ]))
            
        
        if self.date_method == "season":

            months = self.selected_months
            years = self.selected_years

            if not months and not years:
                raise Exception("Please select at least one year ")
                
            elif not months:
                warnings.warn(
                    f'No month(s) selected, executing stack for \
                    all images in {", ".join(str(year) for year in years)}.',
                    SepalWarning
                )
            elif not years:
                warnings.warn(
                    f'No year(s) selected, executing stack for \
                    all images in {", ".join(self.date_selector.selected_months)}.',
                    SepalWarning
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

            ini_date = dt.datetime.strptime(self.start_date, "%Y-%m-%d")
            end_date = dt.datetime.strptime(self.end_date, "%Y-%m-%d")

            filter_images = cs.filter_images_by_date(tifs, ini_date=ini_date, end_date=end_date)

            output_name = param.STACK_DIR / (
                f"{self.prefix}_Stack_{self.selected_stat}_{self.start_date}"
                f"_{self.date_selector.end_date}.tif"
            )
        else:
            filter_images = images
            output_name = param.STACK_DIR/f"{self.prefix}_Stack_{self.selected_stat}.tif"
            
        if not filter_images:
            raise Exception(
                f"There are no images for the selected dates, please try with a"
                " different range."
            )

        elif len(filter_images) == 1:
            raise Exception(
                f"There is only one image in the selected range, to calculate "
                "statistics you need at least 2 images, please try a wider range."
            )
            
        return sorted(filter_images), output_name
    

        