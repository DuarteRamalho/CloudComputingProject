import boto3
from botocore.exceptions import ClientError
import os

class FileStorage:
    def __init__(self):
        self.s3_client = boto3.client('s3',
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name=os.environ.get('AWS_REGION')
        )
        self.bucket_name = os.environ.get('AWS_BUCKET')
        if not self.bucket_name:
            raise ValueError("S3 bucket name not configured")

    def test_connection(self):
        try:
            print("\nAWS Configuration:")
            print(f"AWS Region: {os.environ.get('AWS_REGION', 'Not set')}")
            print(f"AWS Access Key ID: {os.environ.get('AWS_ACCESS_KEY_ID', 'Not set')}")

            secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY', 'Not set')
            masked_secret = secret_key[:4] + '*' * (len(secret_key)-8) + secret_key[-4:] if secret_key != 'Not set' else 'Not set'
            print(f"AWS Secret Access Key: {masked_secret}")
            print(f"S3 Bucket Name: {self.bucket_name}")
            
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            print(f"\nConnection test successful!")
            print(f"Successfully connected to bucket: {self.bucket_name}")
            
            try:
                response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, MaxKeys=5)
                if 'Contents' in response:
                    print("\nFirst 5 objects in bucket:")
                    for obj in response['Contents']:
                        print(f"- {obj['Key']}")
                else:
                    print("\nBucket is empty")
            except Exception as e:
                print(f"\nCould not list bucket contents: {str(e)}")
                
            return True
        
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', 'Unknown')
            print("\nConnection test failed!")
            print(f"Error Code: {error_code}")
            print(f"Error Message: {error_message}")
            
            if error_code == '403':
                print("Bucket exists but you don't have access. Check your AWS credentials and bucket permissions.")
            elif error_code == '404':
                print("Bucket does not exist. Check your bucket name and region.")
            else:
                print(f"Unexpected error occurred while checking bucket.")
            
            return False
        except Exception as e:
            print("\nConnection test failed!")
            print(f"Unexpected error: {str(e)}")
            print("This might indicate incorrect AWS credentials or configuration.")
            return False

    def save_file(self, file, filename, user_id):
        try:
            file_path = self.get_file_path(filename, user_id)
            print(f"Attempting to upload file to path: {file_path}")
            print(f"Using bucket: {self.bucket_name}")
            
            # Ensure file is at the start
            file.seek(0)
            
            self.s3_client.upload_fileobj(
                file,
                self.bucket_name,
                file_path
            )
            print(f"Successfully uploaded file to S3: {file_path}")
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', 'Unknown error')
            print(f"AWS Error - Code: {error_code}, Message: {error_message}")
            return False
        except Exception as e:
            print(f"Unexpected error during file upload: {str(e)}")
            return False

    def get_file_path(self, filename, user_id):
        return f"{user_id}/{filename}"

    def delete_file(self, filename, user_id):
        try:
            file_path = self.get_file_path(filename, user_id)
            print(f"Attempting to delete file: {file_path} from bucket: {self.bucket_name}")
            
            # Check if file exists before deleting
            try:
                self.s3_client.head_object(Bucket=self.bucket_name, Key=file_path)
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    print(f"File not found in S3: {file_path}")
                    return False
                else:
                    raise

            # Delete the file
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            print(f"Successfully deleted file from S3: {file_path}")
            return True
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', 'Unknown error')
            print(f"AWS Error during deletion - Code: {error_code}, Message: {error_message}")
            return False
        except Exception as e:
            print(f"Unexpected error during file deletion: {str(e)}")
            return False

    def download_file(self, filename, user_id):
        try:
            file_path = self.get_file_path(filename, user_id)
            print(f"Attempting to download file: {file_path}")
            
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            print(f"Successfully downloaded file from S3: {file_path}")
            return response['Body'].read()
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', 'Unknown error')
            print(f"AWS Error during download - Code: {error_code}, Message: {error_message}")
            return None
        except Exception as e:
            print(f"Unexpected error during file download: {str(e)}")
            return None
