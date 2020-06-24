## Clean

Warning, this will remove all the changes and update to the latest head

    hg up -C

## Build a documentation

    mkdocs build --clean --site-dir /home/xavier/Projects/SMBYC/smbyc.bitbucket.org/stackcomposed/

## Build and Upload:

    python setup.py sdist bdist_wheel
    twine upload dist/*

## PyInstaller:
    
    pyinstaller --onefile --hidden-import=appdirs --hidden-import=packaging.version --hidden-import=packaging.specifiers --hidden-import=packaging.requirements stack_composed.py
