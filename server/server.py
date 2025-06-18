#!/usr/bin/python

import os
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timezone
import json

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel
import uvicorn
import requests
from dotenv import load_dotenv

import util
from task_integrator import TaskIntegrator, process_and_format_result

class Config:
    def __init__(self):
        self.source_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.source_dir, "..", "data")
        self.integrated_results_dir = os.path.join(self.source_dir, "integrated_results")
        self.predict_url = os.getenv("PREDICT_URL")  
        self.fetch_file_url = "https://gitlab.pavlovia.org/api/v4/projects/{}/repository/files/data%2F{}/raw?ref=master"
        self.gitlab_token = os.getenv("GITLAB_TOKEN")
        self.gitlab_headers = {
            "Authorization": f"Bearer {self.gitlab_token}"
        }
        self.local_headers = {
            "X-GitLab-Token": "tcnl-project",
            "Content-Type": "application/json"
        }
        self.qoca_headers = {
            "Content-Type": "application/json"
        }
        self.exp_gofitt_name = os.getenv("EXPERIMENT_GOFITT_NAME")
        self.exp_ospan_name = os.getenv("EXPERIMENT_OSPAN_NAME")
        self.exp_speechcomp_name = os.getenv("EXPERIMENT_SPEECHCOMP_NAME")
        self.exp_exclusion_name = os.getenv("EXPERIMENT_EXCLUSION_NAME")
        self.exp_textreading_name = os.getenv("EXPERIMENT_TEXTREADING_NAME")
        self.exp_name_list = [self.exp_gofitt_name, self.exp_ospan_name, self.exp_speechcomp_name, self.exp_exclusion_name, self.exp_textreading_name]
        self.platform_features = util.init_platform_features()
        self.missing_marker = -999

def authenticate_gitlab(x_gitlab_token: str = Header(...)):
    if x_gitlab_token != 'tcnl-project':
        raise HTTPException(status_code=403)
    return x_gitlab_token

def fetch_file(project_name, project_id, filename, config, logger):
    resp = requests.get(
        url=config.fetch_file_url.format(project_id, filename), 
        headers=config.gitlab_headers
    )
    if resp.status_code == 200:
        project_dir = os.path.join(config.data_dir, project_name)
        if not os.path.exists(project_dir):
            os.makedirs(project_dir)
        file_path = os.path.join(project_dir, filename)
        if os.path.exists(file_path):
            logger.info(f"File {file_path} already exists, skipping download.")
            return file_path
        else:
            with open(file_path, "wb") as f:
                f.write(resp.content)
            logger.info(f"Successfully fetched file from project {project_name}.")
            return file_path
    else:
        print(f"{resp.text}")
        logger.error(f"Failed to fetch file {filename} from project {project_name}.")
        raise HTTPException(status_code=404, detail=f"File {filename} not found in project {project_name}.")

def convert_np_types(obj):
    if isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist() # Convert np.ndarray to list
    elif isinstance(obj, np.generic): 
        return obj.item() # Convert np.generic to scalar
    elif isinstance(obj, list):
        return [ convert_np_types(i) for i in obj ] 
    elif isinstance(obj, dict):
        return { k: convert_np_types(v) for k, v in obj.items() } 
    else:
        return obj

def update_json_result(subject_id, result_df, config, logger):
    json_file_path = os.path.join(
        config.integrated_results_dir, f"{subject_id}_integrated_result.json"
    )
    if os.path.exists(json_file_path):
        with open(json_file_path, 'r') as json_file:
            existing_data = json.load(json_file)
    else:
        existing_data = { 
            feature: config.missing_marker for feature in config.platform_features 
        }
    result_df = result_df.replace([pd.NA, pd.NaT, float('inf'), float('-inf')], config.missing_marker)
    result_df = result_df.fillna(config.missing_marker)
    formatted_result = process_and_format_result(
        result_df, config.platform_features
    )
    for key, value in formatted_result.items():
        if value != config.missing_marker:
            existing_data[key] = value
        elif key not in existing_data:
            existing_data[key] = config.missing_marker

    with open(json_file_path, 'w') as f:
        json.dump(existing_data, f, indent=2, default=convert_np_types)
    logger.info(f"Successfully updated {json_file_path}")

def process_file(project_name, filepath, config, logger): 
    subject_id = os.path.basename(filepath).split('_')[0]
    
    if project_name == config.exp_gofitt_name:
        result_df = TaskIntegrator().process_subject(subject_id, tasks_to_process=[config.exp_gofitt_name])
    elif project_name == config.exp_ospan_name:
        result_df = TaskIntegrator().process_subject(subject_id, tasks_to_process=[config.exp_ospan_name])
    elif project_name == config.exp_speechcomp_name:
        result_df = TaskIntegrator().process_subject(subject_id, tasks_to_process=[config.exp_speechcomp_name])
    elif project_name == config.exp_exclusion_name:
        result_df = TaskIntegrator().process_subject(subject_id, tasks_to_process=[config.exp_exclusion_name])
    elif project_name == config.exp_textreading_name:
        logger.info(f"Skipping data processing for TextReading")
        result_df = None

    if result_df is not None:
        logger.info(f"Successfully processed data from {project_name}")
        update_json_result(subject_id, result_df, config, logger)
    elif project_name == config.exp_textreading_name:
        logger.info(f"No results for TextReading")
    else:
        logger.warning(f"No results found for {project_name}")

def predict(id_card, config, logger):
    res = requests.get(
        url=f"https://qoca-api.chih-he.dev/user/{id_card}"
    )
    if res.status_code == 200:
        user_info = res.json()
        logger.info("Successfully retrieved user info")

        now = datetime.now(timezone.utc)
        res = requests.post(
            url=config.predict_url, 
            headers=config.local_headers, 
            json={
                "age": user_info['age'],
                "id_card": id_card,
                "name": user_info['name'],
                "test_date": now.strftime('%Y-%m-%dT%H%M%S.') + f"{int(now.microsecond / 1000):03d}Z"
            }
        )
        if (res.status_code == 200):        
            logger.info("Successfully retrieved prediction result")
            return res.json()
        else:
            logger.info("Failed to retrieve prediction result")
            raise Exception(f"{res.text}: {res.status_code}")
    else:
        logger.error("Failed to retrieve user info")
        raise Exception(f"{res.text}: {res.status_code}")

def parse_iso_date(s: str) -> str:
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ", 
        "%Y-%m-%dT%H%M%S.%fZ"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).isoformat()
        except ValueError:
            continue
    # if none of the formats match, raise an error
    raise ValueError(f"Unknown date format: {s!r}")        

def upload_exam(exam, config, logger):
    exam['testDate'] = parse_iso_date(exam['testDate'])
    res = requests.post(
        url='https://qoca-api.chih-he.dev/exams', 
        headers=config.qoca_headers, 
        json=exam
    )
    if (res.status_code == 201):
        json_data = res.json()
        exam_id = json_data['id']
        logger.info(f"Successfully uploaded predict_result (exam_id={exam_id})")
        return exam_id
    else:
        logger.error("Failed to upload predict_result")
        raise Exception(f"{res.text}: {res.status_code}")

def create_task(exam_id, csv_filename, config, logger):
    res = requests.post(
        url='https://qoca-api.chih-he.dev/tasks', 
        headers=config.qoca_headers, 
        json={
            'exam_id': exam_id, 
            'csv_filename': csv_filename
        }
    )
    if (res.status_code == 201):
        logger.info(f"Successfully created report-generating task (exam_id={exam_id})")
    else:
        logger.error(f"Failed to create task report-generating task (exam_id={exam_id})")
        raise Exception(f"{res.text}: {res.status_code}")

## ====================================================================================

load_dotenv()
config = Config()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)  

app = FastAPI(docs_url=None)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks, token: str = Depends(authenticate_gitlab)):
    body = await request.json()
    commits = body.get("commits", [])
    print(f"Received {len(commits)} commits")
    
    project_name = body["project"]["name"]
    project_id = body["project"]["id"]

    for commit in commits:
        if commit["title"].endswith(".csv") and commit["author"]["name"] == "Pavlovia Committer":
            filename = os.path.basename(commit["added"][0])
            logger.info(f"Receiving file: {filename} from project {project_name} ({project_id})")
            
            # try:
            #     if commit["note"] == "a fake commit":
            #         filepath = os.path.join(config.data_dir, project_name, filename)
            #         print("This commit is send from 'pseudo_commit.py'")
            #     else:
            #         raise KeyError
            # except KeyError:
            filepath = fetch_file(project_name, project_id, filename, config, logger)    
            
            process_file(project_name, filepath, config, logger)

            if project_name == config.exp_textreading_name:
                subject_id = os.path.basename(filepath).split('_')[0]
                predict_result = predict(subject_id, config, logger)
                # print(predict_result)
                if predict_result:
                    exam_id = upload_exam(predict_result, config, logger)
                    if exam_id:
                        create_task(exam_id, filename, config, logger)

            return {"status": "ok", "fetched_file": filename}        
        else:
            logger.error(f"No valid commit found in the webhook payload")
            raise HTTPException(status_code=404, detail="No valid commit found!")

@app.post('/report')
async def create_report(request: Request):
    body = await request.json()
    subject_id = body.get("subject_id")

    predict_result = predict(subject_id, config, logger)
    # print(predict_result)
    if predict_result:
        exam_id = upload_exam(predict_result, config, logger)
        return {"status": "ok", 'exam_id': exam_id}
    else:
        raise HTTPException(status_code=422, detail="Failed to produce predict_result")
    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)