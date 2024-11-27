import json
import logging
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from convert import convert_file, make_summary, parse_with_jar
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request
from online_platform_intergration.integrate_all_tasks import (
    TaskIntegrator,
    process_and_format_result,
)
from online_platform_intergration.Textreading_Task.textreading_processor import (
    TextReadingProcessor,
)
from pydantic import BaseModel
import util

load_dotenv()

class SubjectReprocessRequest(BaseModel):
    subject_id: str
    csv_filename: str  # 改為接收 CSV 檔案名稱

# 設置常數和配置
ENDPOINT = "https://gitlab.pavlovia.org/api/v4/projects/{}/repository/files/data%2F{}/raw?ref=master"
DATA_DIR = Path("../data")
ALLOWED_PROJECTS = ["ExclusionTask", "GoFitts", "OspanTask", "SpeechComp", "TextReading"]
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")

# 日誌配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 應用初始化
app = FastAPI(docs_url=None)

PLATFORM_FEATURES = util.init_platform_features()

# 初始化整合器和其他配置
base_path = os.path.dirname(os.path.abspath(__file__))
integrator = TaskIntegrator(base_path)

class SubjectDownloadRequest(BaseModel):
    subject_id: str

def authenticate_gitlab(x_gitlab_token: str = Header(...)):
    if x_gitlab_token != 'tcnl-project':
        raise HTTPException(status_code=403)
    return x_gitlab_token

def fetch_file(project_name, project_id, filename):
    url = ENDPOINT.format(project_id, filename)
    response = requests.get(url, headers={"Authorization": f"Bearer {GITLAB_TOKEN}"})
    project_dir = DATA_DIR / project_name
    project_dir.mkdir(exist_ok=True)
    path = project_dir / filename
    with open(path, "wb") as file:
        file.write(response.content)
    return path

def process_file(project_name, filepath):
    subject_id = filepath.stem.split('_')[0]
    result_df = None

    if project_name == "ExclusionTask":
        result_df = integrator.process_subject(subject_id, tasks_to_process=["exclusion"])
    elif project_name == "OspanTask":
        result_df = integrator.process_subject(subject_id, tasks_to_process=["OspanTask"])
    elif project_name == "SpeechComp":
        result_df = integrator.process_subject(subject_id, tasks_to_process=["SpeechComp"])
    elif project_name == "GoFitts":
        participant, artifact_path = convert_file(filepath)
        if os.path.isfile("GoFitts_modified.jar"):
            parse_with_jar(artifact_path)
            seq_summary_path = Path(artifact_path.parent, f"{artifact_path.stem}-sequence-summary.csv")
            make_summary(participant, filepath, seq_summary_path)
        result_df = integrator.process_subject(subject_id, tasks_to_process=["GoFitts"])
    elif project_name == "TextReading":
        logger.info(f"TextReading 任務目前沒有特定的處理方法")
        return None

    if result_df is not None:
        update_json_result(subject_id, result_df)
    else:
        logger.warning(f"{subject_id} 的 {project_name} 沒有產生任何結果")

    return result_df

def update_json_result(subject_id, result_df):

    # 先處理無效數值
    result_df = result_df.replace([pd.NA, pd.NaT, float('inf'), float('-inf')], -999)
    result_df = result_df.fillna(-999)

    json_file_path = os.path.join(base_path, 'online_platform_intergration', 'integrated_results', f"{subject_id}_integrated_result.json")
    platform_features = PLATFORM_FEATURES
    if not os.path.exists(json_file_path):
        existing_data = {feature: -999 for feature in platform_features}
    else:
        with open(json_file_path, 'r') as json_file:
            existing_data = json.load(json_file)

    formatted_result = process_and_format_result(result_df, platform_features)
    for key, value in formatted_result.items():
        if value != -999:
            existing_data[key] = value
        elif key not in existing_data:
            existing_data[key] = -999

    with open(json_file_path, 'w') as json_file:
        json.dump(existing_data, json_file, indent=2)
    logger.info(f"已更新 {subject_id} 的整合結果，保存至 {json_file_path}")


def reprocess_subject_data(subject_id: str):
    logger.info(f"開始重新處理受試者 ID: {subject_id} 的本地數據")
    
    for project_name in ALLOWED_PROJECTS:
        project_path = DATA_DIR / project_name
        if not project_path.exists():
            logger.warning(f"專案目錄 {project_path} 不存在，跳過此專案")
            continue

        # 遍歷專案目錄下的所有 CSV 文件，並進行篩選
        for filepath in project_path.glob(f"{subject_id}_*.csv"):
            logger.info(f"找到文件: {filepath.name}，正在處理...")
            process_file(project_name, filepath)
    
    logger.info(f"受試者 ID: {subject_id} 的數據已重新處理完畢")

def predict(id_card, test_date):
    user_info = None
    url = f'https://qoca-api.chih-he.dev/user/{id_card}'
    res = requests.get(url=url)
    if (res.status_code == 200):
        user_info = res.json()
        logger.info("取得使用者資訊成功")
    else:
        logger.info("取得使用者資訊失敗")
        return None

    url = 'http://localhost:8888/predict'
    headers = {
        "X-GitLab-Token": "tcnl-project",
        "Content-Type": "application/json"
    }
    json = {
        "age": user_info['age'],
        "id_card": id_card,
        "name": user_info['name'],
        "test_date": test_date,
    }
    res = requests.post(url=url, json=json, headers=headers)
    if (res.status_code == 200):
        logger.info("取得特徵成功")
        return res.json()

    logger.info("取得特徵失敗")
    return None

def upload_exam(exam):
    exam['testDate'] = datetime.strptime(exam['testDate'], "%Y-%m-%dT%H%M%S.%fZ").isoformat()

    url = 'https://qoca-api.chih-he.dev/exams'
    headers = {
        "Content-Type": "application/json"
    }
    res = requests.post(url=url, json=exam, headers=headers)
    if (res.status_code == 201):
        json_data = res.json()
        exam_id = json_data['id']
        logger.info(f"上傳結果成功 exam_id={exam_id}")
        return exam_id

    logger.info(f"上傳結果失敗")
    return None

def create_task(exam_id, csv_filename):
    url = 'https://qoca-api.chih-he.dev/tasks'
    headers = {
        "Content-Type": "application/json"
    }
    task = {
        'exam_id': exam_id,
        'csv_filename': csv_filename
    }
    res = requests.post(url=url, json=task, headers=headers)
    if (res.status_code == 201):
        logger.info("新增任務成功")
        return True

    logger.info(f"新增任務失敗")
    return False

# API 端點
@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks, token: str = Depends(authenticate_gitlab)):
    body = await request.json()
    commits = body.get("commits", [])
    project_name = body["project"]["name"]
    project_id = body["project"]["id"]

    for commit in commits:
        if commit["title"].endswith(".csv") and commit["author"]["name"] == "Pavlovia Committer":
            filename = Path(commit["added"][0]).name
            logger.info(f"正在獲取文件: {filename}，來自專案 {project_name} ({project_id})")
            filepath = fetch_file(project_name, project_id, filename)
            subject_id = filepath.stem.split('_')[0]

            process_file(project_name, filepath)

            if (project_name in ['TextReading', 'TextReading_demo', 'ExclusionTask_JustForDemo']):
                subject_id = filepath.stem.split('_')[0]
                test_date = filepath.stem.split('_')[-1]
                predict_result = predict(subject_id, test_date)
                print(predict_result)
                if predict_result:
                    exam_id = upload_exam(predict_result)
                    if exam_id:
                        create_task(exam_id, filename)
            return {"status": "ok", "fetched_file": filename}

    raise HTTPException(status_code=404, detail="沒有有效的提交！")

# === 主程序入口 ===

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
