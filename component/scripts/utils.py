import io
import json
import logging
from pathlib import Path

import ee
import numpy as np
from apiclient import discovery
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaIoBaseDownload

logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)


class GDrive:
    def __init__(self):
        self.initialize = ee.Initialize()
        # Access to sepal access token
        self.access_token = json.loads(
            (Path.home() / ".config/earthengine/credentials").read_text()
        ).get("access_token")
        self.service = discovery.build(
            serviceName="drive",
            version="v3",
            cache_discovery=False,
            credentials=Credentials(self.access_token),
        )

    def print_file_list(self):
        service = self.service

        results = (
            service.files()
            .list(pageSize=30, fields="nextPageToken, files(id, name)")
            .execute()
        )
        items = results.get("files", [])
        if not items:
            print("No files found.")
        else:
            print("Files:")
            for item in items:
                print("{0} ({1})".format(item["name"], item["id"]))

    def get_items(self):
        service = self.service

        # get list of files
        results = (
            service.files()
            .list(
                q="mimeType='image/tiff'",
                pageSize=1000,
                fields="nextPageToken, files(id, name)",
            )
            .execute()
        )
        items = results.get("files", [])

        return items

    def get_id(self, items_to_search, filename):
        items = items_to_search
        # extract list of names and id and find the wanted file
        namelist = np.array([items[i]["name"] for i in range(len(items))])
        idlist = np.array([items[i]["id"] for i in range(len(items))])
        file_pos = np.where(namelist == filename)

        if len(file_pos[0]) == 0:
            return (0, filename + " not found")
        else:
            return (1, idlist[file_pos])

    def download_file(self, filename, localpath, items_to_search):
        service = self.service

        # get file id
        success, fId = self.get_id(items_to_search, filename)
        if success == 0:
            print(filename + " not found")
            return

        request = service.files().get_media(fileId=fId[0])
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            # print('Download %d%%.' % int(status.progress() * 100))

        fo = open(localpath, "wb")
        fo.write(fh.getvalue())
        fo.close()

    def delete_file(self, items_to_search, filename):
        service = self.service

        # get file id
        success, fId = self.get_id(items_to_search, filename)

        if success == 0:
            print(filename + " not found")

        service.files().delete(fileId=fId[0]).execute()
