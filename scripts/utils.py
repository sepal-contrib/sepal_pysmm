#!/usr/bin/env python3

import ee
import io
import numpy as np
from googleapiclient.http import MediaIoBaseDownload
from apiclient import discovery


class gdrive(object):

    def __init__(self):

        self.credentials = ee.Credentials()
        self.service = discovery.build(serviceName='drive', version='v3', cache_discovery=False, credentials=self.credentials)


    def print_file_list(self):

        service = self.service

        results = service.files().list(
            pageSize=30, fields="nextPageToken, files(id, name)").execute()
        items = results.get('files', [])
        if not items:
            print('No files found.')
        else:
            print('Files:')
            for item in items:
                print('{0} ({1})'.format(item['name'], item['id']))


    def get_id(self, filename):

        service = self.service

        # get list of files
        results = service.files().list(
            pageSize=50, fields="nextPageToken, files(id, name)").execute()
        items = results.get('files', [])

        # extract list of names and id and find the wanted file
        namelist = np.array([items[i]['name'] for i in range(len(items))])
        idlist = np.array([items[i]['id'] for i in range(len(items))])
        file_pos = np.where(namelist == filename)

        if len(file_pos[0]) == 0:
            return(0, filename + ' not found')
        else:
            return(1, idlist[file_pos])


    def download_file(self, filename, localpath):

        service = self.service

        # get file id
        success, fId = self.get_id(filename)
        if success == 0:
            print(filename + ' not found')
            return

        request = service.files().get_media(fileId=fId[0])
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print('Download %d%%.' % int(status.progress() * 100))

        fo = open(localpath, 'wb')
        fo.write(fh.getvalue())
        fo.close()


    def delete_file(self, filename):

        service = self.service

        # get file id
        success, fId = self.get_id(filename)

        if success == 0:
            print(filename + ' not found')

        service.files().delete(fileId=fId[0]).execute()
