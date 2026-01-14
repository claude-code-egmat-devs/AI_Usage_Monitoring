"""
Google Drive API client for file storage
"""

import base64
import json
import logging
import os
from typing import Optional
from io import BytesIO

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from app.config import get_settings

logger = logging.getLogger(__name__)


class GoogleDriveClient:
    """Client for Google Drive API operations"""

    SCOPES = ["https://www.googleapis.com/auth/drive.file"]

    def __init__(self):
        settings = get_settings()
        self.images_folder_id = settings.gdrive_images_folder_id

        # Load credentials
        credentials = self._load_credentials(settings)
        self.service = build("drive", "v3", credentials=credentials)

    def _load_credentials(self, settings) -> service_account.Credentials:
        """Load Google service account credentials"""

        # Try loading from JSON string (base64 encoded)
        if settings.google_service_account_json:
            try:
                json_str = base64.b64decode(settings.google_service_account_json).decode("utf-8")
                info = json.loads(json_str)
                return service_account.Credentials.from_service_account_info(
                    info, scopes=self.SCOPES
                )
            except Exception as e:
                logger.warning(f"Failed to load credentials from JSON string: {e}")

        # Try loading from file path
        if settings.google_service_account_path:
            path = settings.google_service_account_path
            if os.path.exists(path):
                return service_account.Credentials.from_service_account_file(
                    path, scopes=self.SCOPES
                )

        raise ValueError("No valid Google service account credentials found")

    async def create_folder(
        self,
        folder_name: str,
        parent_folder_id: Optional[str] = None,
    ) -> dict:
        """
        Create a new folder in Google Drive.

        Args:
            folder_name: Name of the folder to create
            parent_folder_id: ID of parent folder (default: images folder)

        Returns:
            dict with folder 'id', 'name', and 'webViewLink'
        """
        parent_id = parent_folder_id or self.images_folder_id

        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        }

        try:
            folder = self.service.files().create(
                body=file_metadata,
                fields="id, name, webViewLink"
            ).execute()

            logger.info(f"Created folder: {folder['name']} ({folder['id']})")
            return folder

        except Exception as e:
            logger.error(f"Failed to create folder: {e}")
            raise

    async def upload_image(
        self,
        image_data: bytes,
        file_name: str,
        folder_id: str,
        mime_type: str = "image/png",
    ) -> dict:
        """
        Upload an image to Google Drive.

        Args:
            image_data: Image bytes
            file_name: Name for the file
            folder_id: ID of folder to upload to
            mime_type: MIME type of the image

        Returns:
            dict with file 'id', 'name', and 'webViewLink'
        """
        file_metadata = {
            "name": file_name,
            "parents": [folder_id],
        }

        # Create media upload object
        media = MediaIoBaseUpload(
            BytesIO(image_data),
            mimetype=mime_type,
            resumable=True
        )

        try:
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, name, webViewLink"
            ).execute()

            logger.info(f"Uploaded file: {file['name']} ({file['id']})")
            return file

        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            raise

    async def upload_image_base64(
        self,
        b64_image: str,
        file_name: str,
        folder_id: str,
    ) -> dict:
        """
        Upload a base64 encoded image to Google Drive.

        Args:
            b64_image: Base64 encoded image data
            file_name: Name for the file
            folder_id: ID of folder to upload to

        Returns:
            dict with file info
        """
        image_bytes = base64.b64decode(b64_image)
        return await self.upload_image(
            image_data=image_bytes,
            file_name=file_name,
            folder_id=folder_id,
        )

    async def get_folder_url(self, folder_id: str) -> str:
        """Get the web URL for a folder"""
        try:
            folder = self.service.files().get(
                fileId=folder_id,
                fields="webViewLink"
            ).execute()
            return folder.get("webViewLink", f"https://drive.google.com/drive/folders/{folder_id}")
        except Exception:
            return f"https://drive.google.com/drive/folders/{folder_id}"

    async def list_files_in_folder(self, folder_id: str) -> list[dict]:
        """List all files in a folder"""
        try:
            results = self.service.files().list(
                q=f"'{folder_id}' in parents",
                fields="files(id, name, webViewLink, mimeType)"
            ).execute()
            return results.get("files", [])
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return []

    async def delete_file(self, file_id: str) -> bool:
        """Delete a file from Google Drive"""
        try:
            self.service.files().delete(fileId=file_id).execute()
            logger.info(f"Deleted file: {file_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            return False

    async def make_file_public(self, file_id: str) -> bool:
        """Make a file publicly accessible"""
        try:
            self.service.permissions().create(
                fileId=file_id,
                body={"type": "anyone", "role": "reader"}
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to make file public: {e}")
            return False
