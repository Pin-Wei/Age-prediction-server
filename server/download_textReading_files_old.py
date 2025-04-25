#!/usr/bin/python

import os
import glob
import logging
import time
from datetime import datetime
import shutil
import zipfile
import requests
from dotenv import load_dotenv

class Config:
    def __init__(self):
        self.source_dir = os.path.dirname(os.path.abspath(__file__))
        self.log_dir = os.path.join(self.source_dir, "..", "logs")
        self.log_fn_format = "download_textReading_files_%Y-%m-%d.log"
        self.data_dir = os.path.join(self.source_dir, "..", "data", self.experiment_name)
        self.tmp_dir = os.path.join(self.source_dir, "..", "data", "tmp")
        self.tmp_data_dir = os.path.join(self.tmp_dir, "data")
        self.gitlab_token = os.getenv("GITLAB_TOKEN")
        self.gitlab_header = {
            "oauthToken": self.gitlab_token
        }
        self.experiment_id = os.getenv("EXPERIMENT_TEXTREADING_ID")
        self.experiment_name = os.getenv("EXPERIMENT_TEXTREADING_NAME")
        self.exp_results_url = f"https://pavlovia.org/api/v2/experiments/{self.experiment_id}/results"

def get_download_token(config, logger):
    res = requests.get(
        url=config.exp_results_url, 
        headers=config.gitlab_header
    )
    if res.status_code == 200:        
        json_data = res.json()
        download_token = json_data["downloadToken"]
        logger.info(f"Get download token: {download_token}")
        return download_token
    else:
        logger.error(f"Failed to get download token: {res.status_code}")
        return None

def get_download_url(download_token, config, logger):
    res = requests.get(
        url=os.path.join(config.exp_results_url, download_token, "status"),
        headers=config.gitlab_header
    )
    if res.status_code == 200:
        json_data = res.json()
        download_url = json_data["downloadUrl"]
        filename = download_url.split("/")[-1]
        logger.info(f"Get download URL: {download_url}")
        return download_url, filename
    else:
        logger.error(f"Failed to get download URL: {res.status_code}")
        return None, None

def download_and_extract_zip_file(download_url, zip_file_path, config, logger):
    try:
        with requests.get(download_url, stream=True) as r:
            r.raise_for_status()
            with open(zip_file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        logger.info(f"Downloaded zip file: {zip_file_path}")

        try:
            with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
                zip_ref.extractall(config.tmp_dir)
            logger.info(f"Extracted files to: {config.tmp_dir}")

        except zipfile.BadZipFile:
            logger.error(f"Bad zip file: {zip_file_path}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading file: {e}")

def update_is_file_ready(csv_filename, logger):
    res = requests.get(
        url=f"https://qoca-api.chih-he.dev/tasks?csv_filename={csv_filename}"
    )
    if res.status_code == 200:
        json_data = res.json()

        if len(json_data['items']) > 0:
            task_id = json_data['items'][0]['id']
            status = json_data['items'][0]['status']

            if status == 0: # report is not generated yet 
                res = requests.put(
                    url=f"https://qoca-api.chih-he.dev/tasks/{task_id}", 
                    json={
                        "is_file_ready": 1
                    }
                )
                if res.status_code == 200:
                    logger.info(f"Successfully updated is_file_ready of task #{task_id} to 1.")
                else:
                    logger.error(f"Failed to update is_file_ready of task #{task_id}: {res.status_code}")
    else:
        logger.error(f"Failed to assess report task status for {csv_filename}: {res.status_code}")

## ====================================================================================

if __name__ == "__main__":
    load_dotenv()

    config = Config()
    os.makedirs(config.tmp_dir, exist_ok=True)
    os.makedirs(config.data_dir, exist_ok=True)

    logging.root.handlers = []
    logging.basicConfig(
        level=logging.INFO, 
        filename=os.path.join(config.log_dir, datetime.now().strftime(config.log_fn_format)), 
        format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)4d: %(message)s"
    )
    logger = logging.getLogger(__name__)

    ## Get download token and URL
    download_token = get_download_token(config, logger)

    if download_token is not None:
        download_url, filename = get_download_url(download_token, config, logger)
        time.sleep(10) # wait for the server to prepare the file

        if download_url is not None:
            zip_file_path = os.path.join(config.tmp_dir, filename)
            download_and_extract_zip_file(download_url, zip_file_path, config, logger)

            ## Go through the extracted files and find the CSV files
            csv_files = glob.glob(os.path.join(config.tmp_data_dir, "*.csv"))
            if len(csv_files) == 0:
                logger.error("No CSV files found in the extracted directory.")
            else:
                logger.info(f"Found {len(csv_files)} CSV files.")

                for csv_file in csv_files:
                    csv_filename = os.path.basename(csv_file)
                    update_is_file_ready(csv_filename, logger) # for whose report status is 0

                ## Move the files to the data directory                
                all_files = os.listdir(config.tmp_data_dir)
                for f in all_files:
                    shutil.move(
                        os.path.join(config.tmp_data_dir, f), # source
                        os.path.join(config.data_dir, f) # destination
                    )
                logger.info(f"Moved files to {config.data_dir}")

                ## Remove the temporary directories
                if os.path.isdir(config.tmp_dir):
                    shutil.rmtree(config.tmp_dir)
                    logger.info(f"Removed temporary directory: {config.tmp_dir}")

                if os.path.isdir(config.tmp_data_dir):
                    shutil.rmtree(config.tmp_data_dir)
                    logger.info(f"Removed temporary directory: {config.tmp_data_dir}")
        else:
            logger.error("Failed to get download URL.")
