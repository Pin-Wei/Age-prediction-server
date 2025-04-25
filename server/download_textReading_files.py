#!/usr/bin/python

import os
import glob
import logging
import requests
import pandas as pd
from dotenv import load_dotenv

class Config:
    def __init__(self):
        self.source_dir = os.path.dirname(os.path.abspath(__file__))
        self.experiment_name = os.getenv("EXPERIMENT_TEXTREADING_NAME")
        self.experiment_id = os.getenv("EXPERIMENT_TEXTREADING_ID")
        self.exp_media_url = f"https://pavlovia.org/api/v2/experiments/{self.experiment_id}/media"
        self.gitlab_token = os.getenv("GITLAB_TOKEN")
        self.gitlab_header = {
            "oauthToken": self.gitlab_token
        }
        self.data_dir = os.path.join(self.source_dir, "..", "data", self.experiment_name)

def get_uploaded_not_downloaded(not_downloaded_tokens, config, logger):
    res = requests.get(
        url=config.exp_media_url, 
        headers=config.gitlab_header
    )
    if res.status_code == 200:
        json_data = res.json()
        uploads = json_data["uploads"]
        
        urls_to_download = []
        for upload in uploads:
            session_token = upload["sessionToken"]

            if session_token in not_downloaded_tokens:
                urls_to_download.append(upload["fileUrl"])

        return urls_to_download
    else:
        logger.error(f"Failed to get media list: {res.status_code}")
        return []

def update_is_file_ready(csv_filename, is_file_ready, logger):
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
                        "is_file_ready": is_file_ready
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

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)  

    csv_files = glob.glob(os.path.join(config.data_dir, "*.csv"))
    subj_list = [ os.path.basename(f).split("_")[0] for f in csv_files ]

    webm_files = glob.glob(os.path.join(config.data_dir, "*.webm"))
    webm_subj_list = [ os.path.basename(f).split("_")[0] for f in webm_files ]
    webm_subj_list = list(set(webm_subj_list))

    no_webm_subjs = list(set(subj_list) - set(webm_subj_list))
    logger.info(f"{len(no_webm_subjs)} subjects do not have .webm files yet, start downloading...")

    not_downloaded_tokens = []
    not_ready_csv_filenames = {}
    for subj in no_webm_subjs:
        csv_filepath = glob.glob(os.path.join(config.data_dir, f"{subj}_*.csv"))[0]
        df = pd.read_csv(csv_filepath)
        session_token = df["sessionToken"].values[0]
        not_downloaded_tokens.append(session_token)
        not_ready_csv_filenames[subj] = os.path.basename(csv_filepath)

    urls_to_download = get_uploaded_not_downloaded(
        not_downloaded_tokens, config, logger
    )

    marked_ready_csv_filenames = []
    if len(urls_to_download) > 0:
        for file_url in urls_to_download:
            res = requests.get(file_url, stream=True)

            if res.status_code == 200:
                file_name = os.path.basename(file_url)
                file_path = os.path.join(config.data_dir, file_name)
                with open(file_path, "wb") as f:
                    for chunk in res.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.info(f"Downloaded: {file_url}")

                subj = file_name.split("_")[0]
                if subj not in marked_ready_csv_filenames:
                    csv_filename = not_ready_csv_filenames[subj]
                    update_is_file_ready(
                        csv_filename, 1, logger
                    ) 
                    marked_ready_csv_filenames.append(csv_filename)
            else:
                logger.info("Failed to download. Status code:", res.status_code)
    # else:
    #     logger.info(f"No new files to download.")