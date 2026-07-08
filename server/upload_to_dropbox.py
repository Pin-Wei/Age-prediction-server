#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from pathlib import Path
import subprocess

from dotenv import load_dotenv
import dropbox


class Config:
    def __init__(self):
        self.local_file_path = Path(".") / "predicted_results" / "tidy_predicted_results.csv"
        self.dropbox_folder = "/聽力計畫資料分享"
        self.dropbox_file_path = self.dropbox_folder + "/" + self.local_file_path.name
        self.dropbox_access_token = os.getenv("DROPBOX_ACCESS_TOKEN")


def main():
    config = Config()
    subprocess.run(["python", "tidy_predicted_results.py"])

    try:
        dbx = dropbox.Dropbox(config.dropbox_access_token)
        print(f"Connected to Dropbox account: {dbx.users_get_current_account().email}")
        
        with open(config.local_file_path, "rb") as f:
            dbx.files_upload(
                f.read(), 
                config.dropbox_file_path, 
                mode=dropbox.files.WriteMode.overwrite
            )
        
        print(f"Successfully uploaded '{config.local_file_path.name}' to Dropbox.")

    except Exception as e:
        print(f"Error occurred while uploading file to Dropbox: {e}")

if __name__ == "__main__":  
    load_dotenv()
    main()