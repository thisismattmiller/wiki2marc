#!/bin/bash

rm -fr ./lambda_deploy
rm deploy.zip
mkdir ./lambda_deploy
pip install --target=./lambda_deploy --ignore-installed requests
pip install --target=./lambda_deploy --ignore-installed pymarc

cp 'lambda_function.py' ./lambda_deploy/
cp 'wiki2marc.py' ./lambda_deploy/

cd ./lambda_deploy

zip -r ../deploy.zip *

