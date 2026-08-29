"""
Vibe Vault Storage Adapter
Supports both Local Filesystem Storage (default) and S3-Compatible Object Storage (AWS S3, Cloudflare R2, MinIO, etc.)
"""
import os
import io
from config import Config

# Optional boto3 import
try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None
    ClientError = None


class StorageBackend:
    @staticmethod
    def get_client():
        if not boto3 or Config.STORAGE_BACKEND != 's3':
            return None
        
        session_kwargs = {
            'aws_access_key_id': Config.S3_ACCESS_KEY_ID,
            'aws_secret_access_key': Config.S3_SECRET_ACCESS_KEY,
            'region_name': Config.S3_REGION
        }
        client_kwargs = {}
        if Config.S3_ENDPOINT_URL:
            client_kwargs['endpoint_url'] = Config.S3_ENDPOINT_URL

        return boto3.client('s3', **session_kwargs, **client_kwargs)

    @classmethod
    def save_file(cls, file_obj, subfolder, filename):
        """
        Save a file either to local disk or S3 object storage.
        subfolder: 'songs', 'covers', or 'profiles'
        """
        if Config.STORAGE_BACKEND == 's3' and boto3:
            s3 = cls.get_client()
            key = f"{subfolder}/{filename}"
            content_type = getattr(file_obj, 'content_type', 'application/octet-stream')
            file_obj.seek(0)
            s3.upload_fileobj(
                file_obj,
                Config.S3_BUCKET_NAME,
                key,
                ExtraArgs={'ContentType': content_type}
            )
            return key
        else:
            # Local disk storage
            folder_map = {
                'songs': Config.SONGS_FOLDER,
                'covers': Config.COVERS_FOLDER,
                'profiles': Config.PROFILES_FOLDER
            }
            target_dir = folder_map.get(subfolder, Config.UPLOAD_FOLDER)
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, filename)
            file_obj.seek(0)
            file_obj.save(target_path)
            return target_path

    @classmethod
    def delete_file(cls, subfolder, filename):
        """Delete a file from local disk or S3."""
        if not filename:
            return
        
        if Config.STORAGE_BACKEND == 's3' and boto3:
            try:
                s3 = cls.get_client()
                key = f"{subfolder}/{filename}"
                s3.delete_object(Bucket=Config.S3_BUCKET_NAME, Key=key)
            except Exception as e:
                print(f"[S3 Delete Notice]: {e}")
        else:
            folder_map = {
                'songs': Config.SONGS_FOLDER,
                'covers': Config.COVERS_FOLDER,
                'profiles': Config.PROFILES_FOLDER
            }
            target_dir = folder_map.get(subfolder, Config.UPLOAD_FOLDER)
            target_path = os.path.join(target_dir, filename)
            if os.path.exists(target_path):
                try:
                    os.remove(target_path)
                except Exception as e:
                    print(f"[File Delete Notice]: {e}")

    @classmethod
    def get_file_bytes(cls, subfolder, filename):
        """Retrieve file content bytes for streaming or processing."""
        if Config.STORAGE_BACKEND == 's3' and boto3:
            try:
                s3 = cls.get_client()
                key = f"{subfolder}/{filename}"
                response = s3.get_object(Bucket=Config.S3_BUCKET_NAME, Key=key)
                return response['Body'].read()
            except Exception as e:
                print(f"[S3 Read Error]: {e}")
                return None
        else:
            folder_map = {
                'songs': Config.SONGS_FOLDER,
                'covers': Config.COVERS_FOLDER,
                'profiles': Config.PROFILES_FOLDER
            }
            target_dir = folder_map.get(subfolder, Config.UPLOAD_FOLDER)
            target_path = os.path.join(target_dir, filename)
            if os.path.exists(target_path):
                with open(target_path, 'rb') as f:
                    return f.read()
            return None
