import logging
import os
from datetime import datetime

import requests

_source_dir = os.path.dirname(os.path.abspath(__file__))

LOG_DIR = os.path.join(_source_dir, "../logs")
os.makedirs(LOG_DIR, exist_ok=True)

FORMAT = '%(asctime)s [%(levelname)s] %(filename)s:%(lineno)4d: %(message)s'
logging.root.handlers = []
logging.basicConfig(filename=os.path.join(LOG_DIR, datetime.now().strftime('cronjob_processTasks_%Y-%m-%d.log')), level=logging.INFO, format=FORMAT)
logger = logging.getLogger(__name__)

def process_task(task_id, exam_id, csv_filename):
    subject_id = csv_filename.split('_')[0]
    test_date = os.path.splitext(csv_filename)[0].split('_')[-1]

    url = 'http://localhost:6666/process_textreading'
    headers = {
        "X-GitLab-Token": "tcnl-project",
        "Content-Type": "application/json"
    }
    json_data = {
        "subject_id": subject_id,
        "csv_filename": csv_filename
    }
    res = requests.post(url=url, json=json_data, headers=headers)
    logger.info(f"POST {url} 請求送出成功")
    
    if (res.status_code == 200):
        logger.info("process_textreading 成功")
    else:
        logger.info("process_textreading 失敗")
        return

    user_info = None
    url = f'https://qoca-api.chih-he.dev/user/{subject_id}'
    res = requests.get(url=url)
    if (res.status_code == 200):
        user_info = res.json()
        logger.info("取得使用者資訊成功")
    else:
        logger.info("取得使用者資訊失敗")
        return None

    predict_result = None
    url = 'http://120.126.102.110:8888/predict'
    headers = {
        "X-GitLab-Token": "tcnl-project",
        "Content-Type": "application/json"
    }
    json = {
        "age": user_info['age'],
        "id_card": subject_id,
        "name": user_info['name'],
        "test_date": test_date,
    }
    res = requests.post(url=url, json=json, headers=headers)
    if (res.status_code == 200):
        logger.info("取得特徵成功")
        predict_result = res.json()
    else:
        logger.info("取得特徵失敗")
        return None

    if predict_result:
        url = f"https://qoca-api.chih-he.dev/tasks/{task_id}"
        input_json = {
            "status": 1
        }
        res = requests.put(url=url, json=input_json)
        if (res.status_code == 200):
            logger.info(f"更新 Task id={task_id} 成功")
        else:
            logger.info(f"更新 Task id={task_id} 失敗")
        predict_result['testDate'] = datetime.strptime(predict_result['testDate'], "%Y-%m-%dT%H%M%S.%fZ").isoformat()
        predict_result['report_status'] = 0
        url = f"https://qoca-api.chih-he.dev/exams/{exam_id}"
        res = requests.put(url=url, json=predict_result)
        if res.status_code == 200:
            logger.info(f"更新 Exam id={exam_id} 成功")
        else:
            logger.info(f"更新 Exam id={exam_id} 失敗")

def main():
    LIMIT=1
    url = f"https://qoca-api.chih-he.dev/tasks?size={LIMIT}&is_file_ready=1&status=0"
    res = requests.get(url=url)
    if res.status_code == 200:
        json_data = res.json()
        tasks = json_data['items']
        logger.info(f"Total Tasks: {len(tasks)}")
        for task in tasks:
            id = task['id']
            exam_id = task['exam_id']
            csv_filename = task['csv_filename']
            process_task(id, exam_id, csv_filename)

if __name__ == "__main__":
    logger.info("Start process tasks")
    main()
    logger.info("End process tasks")
