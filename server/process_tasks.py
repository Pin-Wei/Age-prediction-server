#!/usr/bin/python

import os
from datetime import datetime
import logging
import requests
from dotenv import load_dotenv

class Config:
    def __init__(self):
        self.source_dir = os.path.dirname(os.path.abspath(__file__))
        self.log_dir = os.path.join(self.source_dir, "..", "logs")
        self.log_fn_format = "processTasks_%Y-%m-%d.log"
        self.process_textreading_url = os.getenv("PROCESS_TEXTREADING_URL")
        self.predict_url = os.getenv("PREDICT_URL")
        self.local_headers = {
            "X-GitLab-Token": "tcnl-project",
            "Content-Type": "application/json"
        }

def execute_process_textreading(subject_id, csv_filename, config, logger): 
    res = requests.post(
        url=config.process_textreading_url, 
        headers=config.local_headers, 
        json={
            "subject_id": subject_id,
            "csv_filename": csv_filename
        }
    )
    if res.status_code == 200:
        logger.info(f"Successfully sent process_textreading request for {subject_id}")
    else:
        raise Exception(f"Failed to send process_textreading request for {subject_id}: {res.status_code}")

def get_user_info(subject_id, logger):
    res = requests.get(
        url=f'https://qoca-api.chih-he.dev/user/{subject_id}'
    )
    if res.status_code == 200:
        logger.info(f"Successfully retrieved user info for {subject_id}")
        return res.json()
    else:
        raise Exception(f"Failed to retrieve user info for {subject_id}: {res.status_code}")

def get_predict_result(age, subject_id, name, test_date, config, logger):
    res = requests.post(
        url=config.predict_url, 
        headers=config.local_headers, 
        json={
            "age": age, 
            "id_card": subject_id, 
            "name": name, 
            "test_date": test_date
        }
    )
    if res.status_code == 200:
        logger.info(f"Successfully retrieved predict_result for {subject_id}")
        return res.json()
    else:
        raise Exception(f"Failed to retrieve predict_result for {subject_id}: {res.status_code}")

def update_report_status(task_id, status, logger):
    res = requests.put(
        url=f"https://qoca-api.chih-he.dev/tasks/{task_id}", 
        json={
            "status": status
        }
    )
    if res.status_code == 200:
        logger.info(f"Successfully updated report status for task #{task_id} to {status}")
    else:
        raise Exception(f"Failed to update report status for task #{task_id}: {res.status_code}")

def update_predict_result(exam_id, predict_result, logger):
    res = requests.put(
        url=f"https://qoca-api.chih-he.dev/exams/{exam_id}", 
        json=predict_result
    )
    if res.status_code == 200:
        logger.info(f"Successfully updated predict_result for exam #{exam_id}")
    else:
        raise Exception(f"Failed to update predict_result for exam #{exam_id}: {res.status_code}")

## ====================================================================================

if __name__ == "__main__":
    load_dotenv()
    config = Config()
    
    logging.root.handlers = []
    logging.basicConfig(
        level=logging.INFO, 
        filename=os.path.join(config.log_dir, datetime.now().strftime(config.log_fn_format)), 
        format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)4d: %(message)s"
    )
    logger = logging.getLogger(__name__)    
    
    ## Search for tasks that need to be processed (is_file_ready=1 & status=0)
    res = requests.get(
        url="https://qoca-api.chih-he.dev/tasks?is_file_ready=1&status=0"
    )
    if res.status_code == 200:
        json_data = res.json()
        tasks = json_data['items']

        if len(tasks) == 0:
            logger.info("No tasks to process")
        else:
            logger.info(f"Retrieved {len(tasks)} tasks to process")

            for task in tasks:
                task_id = task['id']
                exam_id = task['exam_id']
                csv_filename = task['csv_filename']
                subject_id = csv_filename.split('_')[0]
                test_date = os.path.splitext(csv_filename)[0].split('_')[-1]

                execute_process_textreading(
                    subject_id, csv_filename, config, logger
                )
                user_info = get_user_info(
                    subject_id, logger
                )
                predict_result = get_predict_result(
                    user_info['age'], subject_id, user_info['name'], test_date, config, logger
                )
                if predict_result is not None:
                    update_report_status(task_id, 1, logger) # for the first report

                    predict_result['report_status'] = 0 # for the second report
                    predict_result['testDate'] = datetime.strptime(
                        predict_result['testDate'], "%Y-%m-%dT%H%M%S.%fZ"
                    ).isoformat()
                    update_predict_result(exam_id, predict_result, logger)