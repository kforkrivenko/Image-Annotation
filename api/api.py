from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import pandas as pd
from PIL import Image
import sys
from utils.paths import DATA_DIR, BASE_DIR

# Настройки авторизации
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
FOLDER_ID = "1RvmJMQ-9ru14Jlp5vcX0vDK4l-ShhQZ4"


def get_drive_service():
    if getattr(sys, 'frozen', False):
        secret = DATA_DIR / "client_secret_heraldy.json"
    else:
        secret = BASE_DIR / "client_secret_heraldy.json"
    # Файл token.json сохраняет токены доступа и обновления
    try:
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    except:
        flow = InstalledAppFlow.from_client_secrets_file(
            secret, SCOPES)
        creds = flow.run_local_server(port=0)
        # Сохраняем токены для будущих запросов
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)


def download_xlxs_file(file_id):
    service = get_drive_service()
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()

    fh.seek(0)
    df = pd.read_excel(fh, engine='openpyxl')

    # Вывод данных
    return df


def download_image_file(file_id):
    service = get_drive_service()
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()

    fh.seek(0)
    img = Image.open(fh)

    return img


def list_files():
    service = get_drive_service()
    results = service.files().list(
        q=f"'{FOLDER_ID}' in parents",
        pageSize=10,
        fields="files(id, name, mimeType, size, modifiedTime)"
    ).execute()
    items = results.get('files', [])

    json_file, regions_folder = None, None

    for item in items:
        if item['name'] == 'dataset.xlsx':
            json_file = item
        elif item['name'] == 'Гербы по регионам':
            regions_folder = item

    return json_file, regions_folder


def get_datasets_info():
    json_file, regions_folder = list_files()

    return download_xlxs_file(json_file['id'])


def get_dataset(regions: list[str] | None = None):
    df = get_datasets_info()

    if regions is not None:
        df_regions = df[df['Регион'].isin(regions)]
    else:
        df_regions = df

    for blazon, coat, name, region in zip(df_regions['Блазон'], df_regions['Герб'], df_regions['Название'],
                                          df_regions['Регион']):
        file_id = coat.split('/')[-2]
        yield blazon, download_image_file(file_id), name, region

