# create virtual env
pyenv local 3.9.16
poetry shell
poetry install

# install serverless packages
sls plugin install -n serverless-wsgi
sls plugin install -n serverless-python-requirements
sls plugin install -n serverless-plugin-existing-s3