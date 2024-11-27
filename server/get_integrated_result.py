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


# 初始化整合器和其他配置
base_path = os.path.dirname(os.path.abspath(__file__))
integrator = TaskIntegrator(base_path)

class SubjectDownloadRequest(BaseModel):
    subject_id: str

def authenticate_gitlab(x_gitlab_token: str = Header(...)):
    if x_gitlab_token != 'tcnl-project':
        raise HTTPException(status_code=403)
    return x_gitlab_token

@app.post("/get_integrated_result")
async def get_integrated_result(request: SubjectDownloadRequest, token: str = Depends(authenticate_gitlab)):
    print('接收取得整合資料請求')
    subject_id = request.subject_id
    json_file_path = os.path.join(
        base_path,
        'online_platform_intergration',
        'integrated_results',
        f"{subject_id}_integrated_result.json"
    )

    if not os.path.exists(json_file_path):
        raise HTTPException(status_code=404, detail=f"無法找到受試者 ID: {subject_id} 的整合結果")

    with open(json_file_path, 'r') as json_file:
        integrated_result = json.load(json_file)

    return {"status": "ok", "integrated_result": integrated_result}

# === 主程序入口 ===

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7777)