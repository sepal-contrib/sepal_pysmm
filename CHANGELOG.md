## 0.3.0 (2023-12-11)

### Feat

- use sepal_ui==2.17 to avoid conflicts with ipyleaflet

### Fix

- fix wrong css id for waiting message

### Refactor

- **decorator**: drop debug param

## 0.2.0 (2023-11-23)

### Feat

- update venv and requirements

## 0.1.1 (2023-10-06)

### Refactor

- remove custom_drawer and use sepal_ui oen
- remove legacy file

## 0.1.0 (2023-10-06)

### Feat

- versioning
- fix# 44. make chipping process optional
- remove all time series option from date selection
- add selected orbit to the output
- add latest algorithm to calculate SMM
- refine download process ui
- clean
- define custom span to count values
- add a tasks controller to run in different threads
- task GEE SM processes in chunks and use concurrency
- add comprehensive error message when more than 5k elements on query
- set basepath for fileinput
- forked sepalwidget Alert to set progress on top
- support gdrive connection with latest googleapi
- add alert message, saying statistics are not workking
- create orbit parameter
- closes #20
- set maximum number of selection
- **FolderSelectorTile**: recursively count of content
- new folder selector widget
- **FolderSelector**: first draft to replace current filechooser.

### Fix

- join thread when task is sent
- closes #42
- remove multitemporal despeckle due to timeout computation error
- drop legacy calls on aoi_model. closes #34.
- deactivate progress bars, closes #30
- restart counter to zero
- allow month selection on statistics step
- fix map resize issue. closes #26
- fix datepicker multiple display issues
- parse string. the columns and/or values can be integers
- **StatisticsTile**: bug when selecting season. Improve error messages.
- **FilterTile**: allow recursion
- typo argh
- add model
- typo
- remove lowcase UI
- rename UI
- rename UI
- link v_model with selected_months/years
- trigger resize event
- partially fix #16
- remove leafover

### Refactor

- fix errors on ui
- use sw card to hide the component
- move span to custom widgets
- modifiy logic to track tasks running in GEE
- remove used parameters
- element position and bug fixes - fix error when there's no date selected on statistics (range) - reallocate dates to be displayed inline
- display filter images in inputs section
- use sepal_ui alert to display progress
- add vscode files to .gitignore
- fix small bugs"
- remove unused imports which were causing errors
- remove outdated forked sepal_ui version
- adapt to latest version of sepal_ui==v2.3.1
- **statistics**:  refactor statistics calculation and therefore closes #2 due to a typo
- **StatisticsTile**: adapt to use new FolderSelector widget and improve interactivity
- adapt to new FolderSelectorTile and fill dainamically years/months when folders are selected
- refactor previous date selector widget
- **filter_tile**: integrate last sepal_ui=2.3.1 changes and folder selector
- use fileInput widget to search for tasks files
- **process**: refactor process step
- refactor map tile and adapt to sepal_ui
- refactor filter tile to last sepal_ui version
- adapt statistics tile to last sepal_ui iface
- adadpt process view to the last sepal_ui interface
- adapt download tile to last sepal version
