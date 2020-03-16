#!/bin/bash
# Install Virtual env

echo "Creating virtual env"
cd ~/sepal_pysmm
python3.6 -m venv env2 --system-site-packages
source env/bin/activate

#pip install ipyleaflet
#pip install numpy==1.18
#pip install scipy==1.1.0
pip install scikit-learn==0.21.3

python -m ipykernel install --user --name=env  
deactivate

echo "PYSMM installation complete"