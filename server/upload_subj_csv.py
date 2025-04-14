#!/usr/bin/python

import os
import requests

AUTH_TOKEN = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJueWN1LWFkbWluIiwiZXhwIjoxNzMyNjEzMzU1fQ.tVqszWu0DaklRxdWgQfktBJtrBX0afZu3DSId9G3gTA"

def upload_file(csv_file_path):

    if not os.path.exists(csv_file_path):
        print(f"File {csv_file_path} does not exist :(")
        return None
    else:
        url='https://qoca-api.chih-he.dev/uploadfile'
        headers={
            "Authorization": AUTH_TOKEN
        }
        csv_file = open(csv_file_path, 'rb')
        print(f"Uploading file: '{csv_file_path}'")
        result = requests.post(url=url, headers=headers, files={'file': csv_file})
        csv_file.close()
    
    if result.status_code == 200:
        print("Successfully uploaded file :)")

if __name__ == "__main__":
    csv_file_path = os.path.join("chih-he_uploadfile.csv")
    upload_file(csv_file_path)