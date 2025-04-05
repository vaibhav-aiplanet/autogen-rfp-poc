import logging

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from fastapi import HTTPException

from app.core.config import config


class S3Service:
    def __init__(self):
        try:
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
                region_name=config.AWS_DEFAULT_REGION,
                config=Config(
                    signature_version="s3v4",
                    connect_timeout=10,
                    read_timeout=10,
                ),
            )
            self.bucket_name = config.AWS_BUCKET_NAME
            logging.info("S3 Client Initialized")
            logging.info(f"Bucket Name: {self.bucket_name}")
            logging.info(f"AWS Region: {config.AWS_DEFAULT_REGION}")
            self._validate_bucket_access()
        except Exception as e:
            logging.error(f"S3 Client Initialization Error: {str(e)}")
            raise

    def _validate_bucket_access(self):
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logging.info(f"Successfully accessed bucket: {self.bucket_name}")
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            logging.error(f"Bucket Access Error - Code: {error_code}")
            logging.error(f"Error Message: {error_message}")
            if error_code == "403":
                raise HTTPException(
                    status_code=403,
                    detail=f"Access Forbidden to S3 Bucket: {error_message}",
                )
            elif error_code == "404":
                raise HTTPException(
                    status_code=404, detail=f"Bucket {self.bucket_name} does not exist"
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Unexpected S3 Access Error: {error_message}",
                )

    def generate_presigned_url(
        self,
        file_name: str,
        operation: str = "put_object",
        expiration: int = 3600,
        content_type: str = "",
    ):
        try:
            logging.info(
                f"Generating Presigned URL for file: {file_name}, operation: {operation}"
            )
            params = {
                "Bucket": self.bucket_name,
                "Key": file_name,
            }
            if operation == "put_object" and content_type:
                params["ContentType"] = content_type

            presigned_url = self.s3_client.generate_presigned_url(
                operation, Params=params, ExpiresIn=expiration
            )

            logging.info(f"Presigned URL generated successfully for {file_name}")
            return {
                "url": presigned_url,
                "fields": {
                    "key": file_name,
                    "bucket": self.bucket_name,
                    "content_type": content_type,
                },
            }
        except Exception as e:
            logging.error(f"Presigned URL Generation Error: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"AWS S3 Presigned URL Error: {str(e)}"
            )

    def direct_upload(self, file_content: bytes, file_name: str, content_type: str):
        try:
            logging.info(f"Attempting direct upload for {file_name}")
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_name,
                Body=file_content,
                ContentType=content_type,
            )
            logging.info(f"Direct upload successful for {file_name}")
            return True
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            logging.error(f"Direct Upload Error - Code: {error_code}")
            logging.error(f"Error Message: {error_message}")
            raise HTTPException(
                status_code=403,
                detail=f"S3 Upload Error: {error_code} - {error_message}",
            )
        except Exception as e:
            logging.error(f"Unexpected Direct Upload Error: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Unexpected Direct Upload Error: {str(e)}"
            )

    def get_s3_url(self, object_key: str) -> str:
        return f"https://{self.bucket_name}.s3.amazonaws.com/{object_key}"

    def delete_file_from_s3(self, object_key: str) -> bool:
        """
        Delete a file from S3 by its object key.
        Returns True if deletion is successful.
        """
        try:
            logging.info(f"Deleting file from S3: {object_key}")
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_key)
            logging.info(f"File {object_key} deleted from S3 bucket {self.bucket_name}")
            return True
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            logging.error(f"S3 Delete Error - Code: {error_code}")
            logging.error(f"Error Message: {error_message}")
            raise HTTPException(
                status_code=403,
                detail=f"S3 Delete Error: {error_code} - {error_message}",
            )
        except Exception as e:
            logging.error(f"Unexpected Delete Error: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Unexpected Delete Error: {str(e)}"
            )
