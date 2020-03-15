import httplib2
import os
import argparse
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
from googleapiclient.http import MediaIoBaseDownload
import io
import numpy as np


class gdrive(object):

    def __init__(self):

        # If modifying these scopes, delete your previously saved credentials
        # at ~/.credentials/drive-python-quickstart.json
        self.SCOPES = 'https://www.googleapis.com/auth/drive'
        self.CLIENT_SECRET_FILE = '/home/dguerrero/smm/env/lib/python3.6/site-packages/pysmm/credentials.json'
        self.APPLICATION_NAME = 'Drive API Python Quickstart'


    def _get_credentials(self):
        """Gets valid user credentials from storage.

        If nothing has been stored, or if the stored credentials are invalid,
        the OAuth2 flow is completed to obtain the new credentials.

        Returns:
            Credentials, the obtained credential.
        """

        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(credential_dir,
                                       'drive-python-quickstart.json')
        parser = argparse.ArgumentParser()
        store = Storage(credential_path)
        credentials = store.get()
        if not credentials or credentials.invalid:
            flow = client.flow_from_clientsecrets(self.CLIENT_SECRET_FILE, self.SCOPES)
            flow.user_agent = self.APPLICATION_NAME

            parser = argparse.ArgumentParser(add_help=False)
            parser.add_argument('--logging_level', default='ERROR')
            parser.add_argument('--noauth_local_webserver', action='store_true',
                default=True, help='Do not run a local web server.')
            args = parser.parse_args([])

            credentials = tools.run_flow(flow, store, args)

            print('Storing credentials to ' + credential_path)
        return credentials


    def _init_connection(self):

        credentials = self._get_credentials()
        http = credentials.authorize(httplib2.Http())
        service = discovery.build('drive', 'v3', http=http)

        return(http, service)


    def print_file_list(self):

        http, service = self._init_connection()

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

        http, service = self._init_connection()

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

        http, service = self._init_connection()

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

        http, service = self._init_connection()

        # get file id
        success, fId = self.get_id(filename)

        if success == 0:
            print(filename + ' not found')

        service.files().delete(fileId=fId[0]).execute()
