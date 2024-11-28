import glob
import logging
import os
import shutil
import time
import zipfile
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

_source_dir = os.path.dirname(os.path.abspath(__file__))

LOG_DIR = os.path.join(_source_dir, "../logs")
os.makedirs(LOG_DIR, exist_ok=True)

FORMAT = "%(asctime)s [%(levelname)s] %(filename)s:%(lineno)4d: %(message)s"
logging.root.handlers = []
logging.basicConfig(filename=os.path.join(LOG_DIR, datetime.now().strftime("cronjob_download_textReading_files_%Y-%m-%d.log")), level=logging.INFO, format=FORMAT)
logger = logging.getLogger(__name__)

def main():
    GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")
    EXPERIMENT_TEXTREADING_ID = os.getenv("EXPERIMENT_TEXTREADING_ID")
    DATA_DIR = os.path.join(_source_dir, "../data")

    url = f"https://pavlovia.org/api/v2/experiments/{EXPERIMENT_TEXTREADING_ID}/results"
    headers={
        "oauthToken": GITLAB_TOKEN
    }
    res = requests.get(url=url, headers=headers)
    if res.status_code == 200:
        json_data = res.json()
        download_token = json_data["downloadToken"]
        logger.info(f"Get downloadToken: {download_token}")

        url = f"https://pavlovia.org/api/v2/experiments/{EXPERIMENT_TEXTREADING_ID}/results/{download_token}/status"
        res = requests.get(url=url, headers=headers)
        if res.status_code == 200:
            json_data = res.json()
            download_url = json_data["downloadUrl"]
            filename = download_url.split("/")[-1]
            logger.info(f"Get downloadUrl: {download_url}")

            TMP_DIR = os.path.join(DATA_DIR, "tmp")
            os.makedirs(TMP_DIR, exist_ok=True)

            time.sleep(10)

            path_to_zip_file = os.path.join(TMP_DIR, filename)
            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                with open(path_to_zip_file, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        # If you have chunk encoded response uncomment if
                        # and set chunk_size parameter to None.
                        #if chunk:
                        f.write(chunk)
            logger.info(f"Download zipfile to {path_to_zip_file}")

            with zipfile.ZipFile(path_to_zip_file, "r") as zip_ref:
                zip_ref.extractall(TMP_DIR)
            logger.info(f"Extract zipfile to {TMP_DIR}")

            source_dir = os.path.join(TMP_DIR, "data")
            target_dir = os.path.join(DATA_DIR, "TextReading")

            csv_files = glob.glob(f"{source_dir}/*.csv")
            # update tasks by csv_filename
            logger.info(f"Total csvfiles: {len(csv_files)}")
            for csv_file in csv_files:
                csv_filename = os.path.basename(csv_file)
                url = f"https://qoca-api.chih-he.dev/tasks?csv_filename={csv_filename}"
                res = requests.get(url=url)
                if (res.status_code == 200):
                    json_data = res.json()
                    if len(json_data['items']) > 0:
                        task_id = json_data['items'][0]['id']
                        status = json_data['items'][0]['status']
                        if status == 0:
                            url = f"https://qoca-api.chih-he.dev/tasks/{task_id}"
                            input_json = {
                                "is_file_ready": 1
                            }
                            res = requests.put(url=url, json=input_json)
                            if (res.status_code == 200):
                                logger.info(f"Update Task id={task_id}")

            allfiles = os.listdir(source_dir)
            for f in allfiles:
                src_path = os.path.join(source_dir, f)
                dst_path = os.path.join(target_dir, f)
                shutil.move(src_path, dst_path)
            logger.info(f"Move files from {source_dir} to {target_dir}")

            if os.path.isdir(TMP_DIR):
                shutil.rmtree(TMP_DIR)
                logger.info(f"Remove {TMP_DIR}")

if __name__ == "__main__":
    main()
