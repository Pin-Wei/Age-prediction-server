#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from pathlib import Path
import subprocess

from dotenv import load_dotenv
import dropbox


class Config:
    def __init__(self):
        self.python_path = "/home/aclexp/mambaforge/envs/server/bin/python"

        server_dir = Path(__file__).resolve().parents[0]
        self.script_path = server_dir / "tidy_predicted_results.py"
        self.local_file_path = server_dir / "predicted_results" / "tidy_predicted_results.csv"

        self.dropbox_folder = "/聽力計畫資料分享"
        self.dropbox_file_path = self.dropbox_folder + "/" + self.local_file_path.name
        # self.dropbox_access_token = os.getenv("DROPBOX_ACCESS_TOKEN")
        self.dropbox_refresh_token = os.getenv("DROPBOX_REFRESH_TOKEN")
        self.dropbox_app_key = os.getenv("DROPBOX_APP_KEY")
        self.dropbox_app_secret = os.getenv("DROPBOX_APP_SECRET")


def main():
    config = Config()
    subprocess.run([config.python_path, config.script_path])

    try:
        dbx = dropbox.Dropbox(
            oauth2_refresh_token=config.dropbox_refresh_token,
            app_key=config.dropbox_app_key,
            app_secret=config.dropbox_app_secret
        )
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