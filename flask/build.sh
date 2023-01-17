# create virtual env
virtualenv -p python3.9 venv
. venv/bin/activate
pip install -r requirements.txt

# install serverless packages
sls plugin install -n serverless-wsgi
sls plugin install -n serverless-python-requirements