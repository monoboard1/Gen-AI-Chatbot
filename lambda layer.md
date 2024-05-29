# Create AWS Lambda Layer
### Run a docker container
`docker pull amazonlinux:2023`

`docker run -it -v "%cd%/lambda-layer/lambda-layer" amazonlinux:2023 /bin/bash`

### install python 3.11
`yum install python3.11 -y`

`yum install zip`

### Create virtual environment and install packages
`python3.11 -m venv my_lambda_env`  
`source my_lambda_env/bin/activate`  
`pip install packages`  
install any package

### Prepare the Lambda Layer and upload it to S3
`mkdir -p /lambda-layer/python/lib/python3.11/site-packages`  
`cp -r my_lambda_env/lib/python3.11/site-packages/* /lambda-layer/python/lib/python3.11/site-packages/`  
`cd /lambda-layer`  
`zip -r {package_name}.zip python`  