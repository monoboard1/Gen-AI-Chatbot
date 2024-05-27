### Uploading recursively with AWS CLI

_set up credential:_  
`aws configure`  
_uploading:_  
`aws s3 cp yourfolder s3://your S3 bucket/foler/ --recursive`  
- don't add a forward slash after your folder 
- you can use an absolute path or use the command within the path containing the target folder.