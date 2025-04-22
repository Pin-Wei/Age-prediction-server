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
        logger.info(f"成功送出 process_textreading 請求")

    ## Get user info
    res = requests.get(
        url=f'https://qoca-api.chih-he.dev/user/{subject_id}'
    )
    if res.status_code == 200:
        user_info = res.json()
        logger.info("成功取得受試者資訊")
    else:
        user_info = None
        logger.info("受試者資訊取得失敗")

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
        logger.info("成功取得預測結果")
    else:
        predict_result = None
        logger.info("預測結果取得失敗")
    
    if predict_result is not None:

        ## Update report status
        res = requests.put(
            url=f"https://qoca-api.chih-he.dev/tasks/{task_id}", 
            json={
                "status": 1
            }
        )
        if res.status_code == 200:
            logger.info(f"更新任務 #{task_id} 狀態為 1")
        else:
            logger.error(f"更新任務 #{task_id} 狀態失敗: {res.status_code}")

        predict_result['testDate'] = datetime.strptime(predict_result['testDate'], "%Y-%m-%dT%H%M%S.%fZ").isoformat()
        predict_result['report_status'] = 0
        res = requests.put(
            url=f"https://qoca-api.chih-he.dev/exams/{exam_id}", 
            json=predict_result
        )
        if res.status_code == 200:
            logger.info(f"成功更新報告編號 #{exam_id} 的預測結果")
        else:
            logger.error(f"報告編號 #{exam_id} 的預測結果更新失敗: {res.status_code}")

def main():
    load_dotenv()
    config = Config()
    
    logging.root.handlers = []
    logging.basicConfig(
        level=logging.INFO, 
        filename=os.path.join(config.log_dir, datetime.now().strftime("cronjob_processTasks_%Y-%m-%d.log")), 
        format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)4d: %(message)s"
    )
    logger = logging.getLogger(__name__)    
    logger.info("=== 開始執行 process_tasks.py ===")
    
    ## Search for tasks that need to be processed (is_file_ready=1 & status=0)
    res = requests.get(
        url="https://qoca-api.chih-he.dev/tasks?size=1&is_file_ready=1&status=0"
    )
    if res.status_code == 200:
        json_data = res.json()
        tasks = json_data['items']
        logger.info(f"成功取得 {len(tasks)} 筆任務數據")
        for task in tasks:
            process_task(
                task['id'], task['exam_id'], task['csv_filename'], config, logger
            )

    logger.info("=== process_tasks.py 任務終了 ===")

if __name__ == "__main__":
    main()