
import os
import json
import requests
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header, Depends, BackgroundTasks, Request
from pydantic import BaseModel
import pandas as pd

from convert import convert_file, parse_with_jar, make_summary
from online_platform_intergration.integrate_all_tasks import TaskIntegrator, process_and_format_result
from online_platform_intergration.Textreading_Task.textreading_processor import TextReadingProcessor
from dotenv import load_dotenv

load_dotenv() 

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

PLATFORM_FEATURES = [
    "MOTOR_GOFITTS_BEH_ID1_LeaveTime", "MOTOR_GOFITTS_BEH_ID2_LeaveTime",
    "MOTOR_GOFITTS_BEH_ID3_LeaveTime", "MOTOR_GOFITTS_BEH_ID4_LeaveTime",
    "MOTOR_GOFITTS_BEH_ID5_LeaveTime", "MOTOR_GOFITTS_BEH_ID6_LeaveTime",
    "MOTOR_GOFITTS_BEH_ID1_PointTime", "MOTOR_GOFITTS_BEH_ID2_PointTime",
    "MOTOR_GOFITTS_BEH_ID3_PointTime", "MOTOR_GOFITTS_BEH_ID4_PointTime",
    "MOTOR_GOFITTS_BEH_ID5_PointTime", "MOTOR_GOFITTS_BEH_ID6_PointTime",
    "MOTOR_GOFITTS_BEH_SLOPE_LeaveTime", "MOTOR_GOFITTS_BEH_SLOPE_PointTime",
    "MEMORY_EXCLUSION_BEH_C1_FAMILIARITY", "MEMORY_EXCLUSION_BEH_C2_FAMILIARITY",
    "MEMORY_EXCLUSION_BEH_C3_FAMILIARITY", "MEMORY_EXCLUSION_BEH_C1_RECOLLECTION",
    "MEMORY_EXCLUSION_BEH_C2_RECOLLECTION", "MEMORY_EXCLUSION_BEH_C3_RECOLLECTION",
    "MEMORY_EXCLUSION_BEH_C1TarHit_PROPORTION", "MEMORY_EXCLUSION_BEH_C1TarMiss_PROPORTION",
    "MEMORY_EXCLUSION_BEH_C1NonTarFA_PROPORTION", "MEMORY_EXCLUSION_BEH_C1NonTarCR_PROPORTION",
    "MEMORY_EXCLUSION_BEH_C1NewFA_PROPORTION", "MEMORY_EXCLUSION_BEH_C1NewCR_PROPORTION",
    "MEMORY_EXCLUSION_BEH_C1NonTarFA_RT", "MEMORY_EXCLUSION_BEH_C1NonTarCR_RT",
    "MEMORY_EXCLUSION_BEH_C1NewFA_RT", "MEMORY_EXCLUSION_BEH_C1NewCR_RT",
    "MEMORY_EXCLUSION_BEH_C2TarHit_PROPORTION", "MEMORY_EXCLUSION_BEH_C2TarMiss_PROPORTION",
    "MEMORY_EXCLUSION_BEH_C2NonTarFA_PROPORTION", "MEMORY_EXCLUSION_BEH_C2NonTarCR_PROPORTION",
    "MEMORY_EXCLUSION_BEH_C2NewFA_PROPORTION", "MEMORY_EXCLUSION_BEH_C2NewCR_PROPORTION",
    "MEMORY_EXCLUSION_BEH_C2TarHit_RT", "MEMORY_EXCLUSION_BEH_C2TarMiss_RT",
    "MEMORY_EXCLUSION_BEH_C2NonTarFA_RT", "MEMORY_EXCLUSION_BEH_C2NonTarCR_RT",
    "MEMORY_EXCLUSION_BEH_C2NewFA_RT", "MEMORY_EXCLUSION_BEH_C2NewCR_RT",
    "MEMORY_EXCLUSION_BEH_C3TarHit_PROPORTION", "MEMORY_EXCLUSION_BEH_C3TarMiss_PROPORTION",
    "MEMORY_EXCLUSION_BEH_C3NonTarFA_PROPORTION", "MEMORY_EXCLUSION_BEH_C3NonTarCR_PROPORTION",
    "MEMORY_EXCLUSION_BEH_C3NewFA_PROPORTION", "MEMORY_EXCLUSION_BEH_C3NewCR_PROPORTION",
    "MEMORY_EXCLUSION_BEH_C3TarHit_RT", "MEMORY_EXCLUSION_BEH_C3TarMiss_RT",
    "MEMORY_EXCLUSION_BEH_C3NonTarFA_RT", "MEMORY_EXCLUSION_BEH_C3NonTarCR_RT",
    "MEMORY_EXCLUSION_BEH_C3NewFA_RT", "MEMORY_EXCLUSION_BEH_C3NewCR_RT",
    "MEMORY_OSPAN_BEH_LETTER_ACCURACY", "MEMORY_OSPAN_BEH_MATH_ACCURACY",
    "LANGUAGE_SPEECHCOMP_BEH_PASSIVE_ACCURACY",
    "LANGUAGE_SPEECHCOMP_BEH_PASSIVE_RT", "LANGUAGE_READING_BEH_NULL_MeanSR"
]

# 初始化整合器和其他配置
base_path = os.path.dirname(os.path.abspath(__file__))
integrator = TaskIntegrator(base_path)

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

def process_text_reading(subject_id):
    audio_files = list(DATA_DIR.glob(f"TextReading/{subject_id}_*.webm"))
    if audio_files:
        logger.info(f"找到 {len(audio_files)} 個音頻文件供 {subject_id} 處理")
        text_reading_processor = TextReadingProcessor(
            input_path=DATA_DIR / "TextReading",
            output_path=DATA_DIR / "TextReading"
        )
        
        csv_files = []
        for audio_file in audio_files:
            logger.info(f"處理音頻文件：{audio_file}")
            csv_file = text_reading_processor.generate_csv(audio_file)
            if csv_file:
                csv_files.append(csv_file)
        
        if csv_files:
            mean_speech_rate = text_reading_processor.calculate_mean_syllable_speech_rate(csv_files)
            if mean_speech_rate is not None:
                result_df = pd.DataFrame({
                    'ID': [subject_id],
                    'LANGUAGE_READING_BEH_NULL_MeanSR': [mean_speech_rate]
                })
                update_json_result(subject_id, result_df)
            else:
                logger.warning(f"未能成功計算出 {subject_id} 的平均語速")
        else:
            logger.warning(f"未能生成 {subject_id} 的任何 .words.csv 文件")
    else:
        logger.warning(f"未找到 {subject_id} 的任何 .webm 音頻文件")

def update_json_result(subject_id, result_df):
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

class SubjectReprocessRequest(BaseModel):
    subject_id: str

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

            if project_name == "TextReading":
                background_tasks.add_task(process_text_reading, subject_id)
            else:
                process_file(project_name, filepath)
                
            return {"status": "ok", "fetched_file": filename}
    
    raise HTTPException(status_code=404, detail="沒有有效的提交！")

@app.post("/download_all")
async def download_all_files(background_tasks: BackgroundTasks, token: str = Depends(authenticate_gitlab)):
    background_tasks.add_task(fetch_all_files)
    return {"status": "started", "message": "開始下載所有文件"}

def fetch_all_files():
    projects_url = "https://gitlab.pavlovia.org/api/v4/projects"
    headers = {"Authorization": f"Bearer {GITLAB_TOKEN}"}

    response = requests.get(projects_url, headers=headers, params={"membership": True})
    response.raise_for_status()
    projects = response.json()

    logger.info(f"找到 {len(projects)} 個專案")

    for project in projects:
        project_id = project['id']
        project_name = project['name']

        if project_name not in ALLOWED_PROJECTS:
            logger.info(f"跳過專案: {project_name} (不在允許列表中)")
            continue

        logger.info(f"處理專案: {project_name} (ID: {project_id})")

        files = get_project_files(project_id)
        if files:
            for file in files:
                if file['type'] == 'blob' and file['name'].endswith('.csv'):
                    filename = file['name']
                    if "demo" in filename.lower():
                        logger.info(f"跳過演示文件: {filename}")
                        continue
                    logger.info(f"下載文件: {filename} 從專案 {project_name} ({project_id})")
                    filepath = fetch_file(project_name, project_id, filename)
                    if filepath:
                        process_file(project_name, filepath)
        else:
            logger.warning(f"無法獲取專案 {project_name} 的文件列表。")

    logger.info("所有文件下載完成")

class SubjectDownloadRequest(BaseModel):
    subject_id: str

@app.post("/download_by_subject")
async def download_by_subject(request: SubjectDownloadRequest, token: str = Depends(authenticate_gitlab)):
    subject_id = request.subject_id
    logger.info(f"開始下載受試者 ID: {subject_id} 的文件")

    downloaded_files = []

    for project_name in ALLOWED_PROJECTS:
        project_id = get_project_id(project_name)
        if project_id is None:
            logger.warning(f"無法找到專案 {project_name} 的 ID")
            continue

        files = get_project_files(project_id)
        if files is None:
            logger.warning(f"無法獲取專案 {project_name} 的文件列表")
            continue

        for file in files:
            if file['type'] == 'blob' and file['name'].endswith('.csv'):
                filename = file['name']
                if subject_id in filename and "demo" not in filename.lower():
                    logger.info(f"下載文件: {filename} 從專案 {project_name}")
                    filepath = fetch_file(project_name, project_id, filename)
                    if filepath:
                        downloaded_files.append(str(filepath))
                        process_file(project_name, filepath)

    if not downloaded_files:
        return {"status": "error", "message": f"未找到受試者 ID: {subject_id} 的文件"}

    return {"status": "ok", "downloaded_files": downloaded_files}

@app.post("/get_integrated_result")
async def get_integrated_result(request: SubjectDownloadRequest, token: str = Depends(authenticate_gitlab)):
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

@app.post("/reprocess")
async def reprocess_subject(request: SubjectReprocessRequest, background_tasks: BackgroundTasks, token: str = Depends(authenticate_gitlab)):
    subject_id = request.subject_id
    logger.info(f"開始重新處理受試者 ID: {subject_id} 的數據")

    # 從所有允許的專案中重新處理受試者數據
    background_tasks.add_task(reprocess_subject_data, subject_id)
    background_tasks.add_task(process_text_reading, subject_id)

    return {"status": "processing", "message": f"受試者 ID: {subject_id} 的數據正在重新處理"}


# === 主程序入口 ===

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
