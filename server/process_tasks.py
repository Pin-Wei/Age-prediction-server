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

def process_task(task_id, exam_id, csv_filename, config, logger):
    subject_id = csv_filename.split('_')[0]

    ## Send process_textreading request
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
        logger.error(f"Failed to send process_textreading request for {subject_id}")

    ## Get user info
    res = requests.get(
        url=f'https://qoca-api.chih-he.dev/user/{subject_id}'
    )
    if res.status_code == 200:
        user_info = res.json()
        logger.info(f"Successfully retrieved user info for {subject_id}")
    else:
        user_info = None
        logger.error(f"Failed to retrieve user info for {subject_id}")

    ## Send predict request
    test_date = os.path.splitext(csv_filename)[0].split('_')[-1]
    res = requests.post(
        url=config.predict_url, 
        headers=config.local_headers, 
        json={
            "age": user_info['age'], 
            "id_card": subject_id, 
            "name": user_info['name'], 
            "test_date": test_date
        }
    )
    if res.status_code == 200:
        predict_result = res.json()
        logger.info(f"Successfully retrieved predict_result for {subject_id}")
    else:
        predict_result = None
        logger.error(f"Failed to retrieve predict_result for {subject_id}")
    
    if predict_result is not None:

        ## Update report status
        res = requests.put(
            url=f"https://qoca-api.chih-he.dev/tasks/{task_id}", 
            json={
                "status": 1
            }
        )
        if res.status_code == 200:
            logger.info(f"Successfully update task #{task_id} status to 1")
        else:
            logger.error(f"Failed to update task #{task_id}: {res.status_code}")

        predict_result['testDate'] = datetime.strptime(predict_result['testDate'], "%Y-%m-%dT%H%M%S.%fZ").isoformat()
        predict_result['report_status'] = 0
        res = requests.put(
            url=f"https://qoca-api.chih-he.dev/exams/{exam_id}", 
            json=predict_result
        )
        if res.status_code == 200:
            logger.info(f"Successfully update predict_result for exam #{exam_id}")
        else:
            logger.error(f"Failed to update predict_result for exam #{exam_id}: {res.status_code}")

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
                process_task(
                    task['id'], task['exam_id'], task['csv_filename'], config, logger
                )
    else:
        logger.error(f"Failed to retrieve tasks: {res.status_code}")