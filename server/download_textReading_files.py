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
        self.gitlab_token = os.getenv("GITLAB_TOKEN")
        self.experiment_id = os.getenv("EXPERIMENT_TEXTREADING_ID")
        self.experiment_name = os.getenv("EXPERIMENT_TEXTREADING_NAME")
        self.source_dir = os.path.dirname(os.path.abspath(__file__))
        self.log_dir = os.path.join(self.source_dir, "..", "logs")
        self.data_dir = os.path.join(self.source_dir, "..", "data", self.experiment_name)
        self.tmp_dir = os.path.join(self.source_dir, "..", "data", "tmp")
        self.tmp_data_dir = os.path.join(self.tmp_dir, "data")

def main():
    load_dotenv()
    config = Config()
    
    logging.root.handlers = []
    logging.basicConfig(
        level=logging.INFO, 
        filename=os.path.join(config.log_dir, datetime.now().strftime("cronjob_download_textReading_files_%Y-%m-%d.log")), 
        format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)4d: %(message)s"
    )
    logger = logging.getLogger(__name__)

    ## Get download token and download URL
    url = f"https://pavlovia.org/api/v2/experiments/{config.experiment_id}/results"
    headers = {"oauthToken": config.gitlab_token}
    res = requests.get(url=url, headers=headers)
    if res.status_code == 200:        
        json_data = res.json()
        download_token = json_data["downloadToken"]
        logger.info(f"Get download token: {download_token}")

        url = f"https://pavlovia.org/api/v2/experiments/{config.experiment_id}/results/{download_token}/status"
        res = requests.get(url=url, headers=headers)
        if res.status_code == 200:
            json_data = res.json()
            download_url = json_data["downloadUrl"]
            filename = download_url.split("/")[-1]
            logger.info(f"Get download URL: {download_url}")

            ## Wait for the server to prepare the file
            time.sleep(10) 

            ## Download the zip file
            if not os.path.exists(config.tmp_dir):
                os.makedirs(config.tmp_dir)
            zip_file_path = os.path.join(config.tmp_dir, filename)

            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                with open(zip_file_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            logger.info(f"Downloaded zip file: {zip_file_path}")
            
            ## Extract the files
            with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
                zip_ref.extractall(config.tmp_dir)
            logger.info(f"Extracted files to: {config.tmp_dir}")

            ## Go through the extracted files and find the CSV files
            csv_files = glob.glob(os.path.join(config.tmp_data_dir, "*.csv"))
            if len(csv_files) == 0:
                logger.error("No CSV files found in the extracted directory.")
            else:
                logger.info(f"Found {len(csv_files)} CSV files.")

                for csv_file in csv_files:
                    csv_filename = os.path.basename(csv_file)

                    ## Check report status (0: not generated yet, 1: generated)
                    url = f"https://qoca-api.chih-he.dev/tasks?csv_filename={csv_filename}"
                    res = requests.get(url=url)
                    if (res.status_code == 200):
                        json_data = res.json()
                        if len(json_data['items']) > 0:
                            task_id = json_data['items'][0]['id']
                            status = json_data['items'][0]['status']

                            if status == 0: # update 'is_file_ready' to 1
                                res = requests.put(
                                    url=f"https://qoca-api.chih-he.dev/tasks/{task_id}", 
                                    json={
                                        "is_file_ready": 1
                                    }
                                )
                                if res.status_code == 200:
                                    logger.info(f"Updated task #{task_id} to ready.")
                                else:
                                    logger.error(f"Failed to update task #{task_id}: {res.status_code}")
                    else:
                        logger.error(f"Failed to assess report task status for {csv_filename}: {res.status_code}")

                ## Move the files to the data directory
                if not os.path.exists(config.data_dir):
                    os.makedirs(config.data_dir)
                all_files = os.listdir(config.tmp_data_dir)
                for f in all_files:
                    shutil.move(
                        os.path.join(config.tmp_data_dir, f), # source
                        os.path.join(config.data_dir, f) # destination
                    )
                logger.info(f"Moved files to {config.data_dir}")

                if os.path.isdir(config.tmp_data_dir):
                    shutil.rmtree(config.tmp_data_dir)
                    logger.info(f"Removed temporary directory: {config.tmp_data_dir}")
        else:
            logger.error(f"Failed to get download link: {res.status_code}")

if __name__ == "__main__":
    main()
