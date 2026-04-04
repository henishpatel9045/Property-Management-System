import os
import io
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError

class GoogleAuthRevokedError(Exception):
    pass

class DriveQuotaExceededError(Exception):
    pass

def get_drive_service(user):
    if not user.google_credentials:
        raise GoogleAuthRevokedError("No Google credentials found.")
        
    creds_dict = user.google_credentials
    creds = Credentials(
        token=creds_dict.get('token'),
        refresh_token=creds_dict.get('refresh_token'),
        token_uri=creds_dict.get('token_uri'),
        client_id=creds_dict.get('client_id'),
        client_secret=creds_dict.get('client_secret'),
        scopes=creds_dict.get('scopes')
    )
    
    try:
        service = build('drive', 'v3', credentials=creds)
        # Attempt a quick API call to trigger a token refresh if expired.
        # If the refresh token is also invalid, it throws RefreshError.
        service.about().get(fields="user").execute()
        return service
    except RefreshError:
        user.google_credentials = None
        user.save()
        raise GoogleAuthRevokedError("Google Auth expired or revoked.")
    except Exception as e:
        raise e

def _get_or_create_nested_folder(service, path_array):
    parent_id = None
    
    for folder_name in path_array:
        # Sanitize folder_name to avoid query injection breaks
        safe_name = folder_name.replace("'", "\\'")
        query = f"name='{safe_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
            
        results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])
        
        if items:
            parent_id = items[0].get('id')
        else:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_id:
                file_metadata['parents'] = [parent_id]
            folder = service.files().create(body=file_metadata, fields='id').execute()
            parent_id = folder.get('id')
            
    return parent_id

def upload_file_to_drive(user, file_obj, display_name, mime_type, path_array=None):
    service = get_drive_service(user)
    if not path_array:
        path_array = ["PropertyMaps"]
        
    folder_id = _get_or_create_nested_folder(service, path_array)
    
    file_metadata = {
        'name': display_name,
        'parents': [folder_id]
    }
    
    media = MediaIoBaseUpload(file_obj, mimetype=mime_type, resumable=True)
    
    try:
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return file.get('id')
    except HttpError as error:
        if error.status_code == 403 and ('quota' in str(error).lower() or 'storage' in str(error).lower()):
            raise DriveQuotaExceededError("Not enough space in your Google Drive.")
        raise error

def download_file_stream(user, file_id):
    service = get_drive_service(user)
    
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        
    fh.seek(0)
    metadata = service.files().get(fileId=file_id, fields='name, mimeType').execute()
    
    return fh, metadata.get('name', 'downloaded_file'), metadata.get('mimeType', 'application/octet-stream')

def delete_file_from_drive(user, file_id):
    if not file_id:
        return
    service = get_drive_service(user)
    try:
        service.files().delete(fileId=file_id).execute()
    except HttpError as error:
        # Ignore if file is already deleted or not found
        if error.status_code != 404:
            raise error
