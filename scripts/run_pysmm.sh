#!/bin/bash
echo 'The soil moisture maps are exporting to your google drive.'
nohup $1 ./scripts/run_pysmm.py "$2" "$3" "$4" $5 $6 $7 $8 $9 & >./nohup.out 2>&1
tail -f ./nohup.out
