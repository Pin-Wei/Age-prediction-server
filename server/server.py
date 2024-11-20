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

def process_text_reading(subject_id: str, csv_filename: str) -> dict:
    result = {
        "status": "error",
        "message": "",
        "files_processed": [],
        "mean_speech_rate": None,
        "success": False,
        "csv_filename": csv_filename
    }
    
    # 讀取 CSV 檔案取得日期
    csv_path = DATA_DIR / "TextReading" / csv_filename
    if not csv_path.exists():
        result["message"] = f"找不到 CSV 檔案：{csv_filename}"
        return result
    
    try:
        df = pd.read_csv(csv_path)
        test_date = df['date'].iloc[0]  # 格式如：2024-10-29_11h04.28.020
        # 不需要轉換格式，直接使用原始格式
        logger.info(f"從 CSV 讀取到的日期: {test_date}")
    except Exception as e:
        result["message"] = f"讀取 CSV 檔案失敗：{str(e)}"
        return result
    
    # 構建音檔匹配模式，使用原始格式
    pattern = f"TextReading/{subject_id}_TextReading_{test_date}_recording_mic_*.webm"
    logger.info(f"搜尋音檔的模式: {pattern}")
    audio_files = list(DATA_DIR.glob(pattern))
    
    if not audio_files:
        result["message"] = f"未找到受試者 {subject_id} 在 {test_date} 的任何音頻文件"
        return result
        
    logger.info(f"找到 {len(audio_files)} 個音頻文件供 {subject_id} 處理")
    result["files_processed"] = [f.name for f in audio_files]
    
    text_reading_processor = TextReadingProcessor(
        input_path=DATA_DIR / "TextReading",
        output_path=DATA_DIR / "TextReading"
    )

    csv_files = []
    for audio_file in audio_files:
        logger.info(f"處理音頻文件：{audio_file}")
        try:
            csv_file = text_reading_processor.generate_csv(audio_file)
            if csv_file:
                csv_files.append(csv_file)
        except Exception as e:
            logger.error(f"處理音頻文件 {audio_file} 時發生錯誤：{str(e)}")

    if csv_files:
        try:
            mean_speech_rate = text_reading_processor.calculate_mean_syllable_speech_rate(csv_files)
            if mean_speech_rate is not None:
                result_df = pd.DataFrame({
                    'ID': [subject_id],
                    'LANGUAGE_READING_BEH_NULL_MeanSR': [mean_speech_rate]
                })
                update_json_result(subject_id, result_df)
                result.update({
                    "status": "success",
                    "message": "成功處理音頻文件並計算平均語速",
                    "mean_speech_rate": mean_speech_rate,
                    "success": True
                })
            else:
                result["message"] = "未能成功計算出平均語速"
        except Exception as e:
            result["message"] = f"計算平均語速時發生錯誤：{str(e)}"
    else:
        result["message"] = "未能生成任何 .words.csv 文件"
    
    return result

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
    now = datetime.now()

    user_info = None
    url = f'https://qoca-api.chih-he.dev/user/{id_card}'
    res = requests.get(url=url)
    if (res.status_code == 200):
        user_info = res.json()
    else:
        return None

    url = 'http://120.126.102.110:8888/predict'
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
    url = 'https://qoca-api.chih-he.dev/exams'
    headers = {
        "Content-Type": "application/json"
    }
    res = requests.post(url=url, json=exam, headers=headers)
    if (res.status_code == 201):
        logger.info("上傳結果成功")
        return True

    logger.info(f"上傳結果失敗")
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

            if project_name == "TextReading":
                background_tasks.add_task(process_text_reading, subject_id)
            else:
                process_file(project_name, filepath)

            if (project_name in ['ExclusionTask', 'ExclusionTask_JustForDemo']):
                subject_id = filepath.stem.split('_')[0]
                test_date = filepath.stem.split('_')[-1]
                test_date = datetime.strptime(test_date, "%Y-%m-%dT%H%M%S.%fZ") # .strftime("%Y-%m-%d")
                predict_result = predict(subject_id, test_date)
                if predict_result:
                    upload_exam(predict_result)
            return {"status": "ok", "fetched_file": filename}

    raise HTTPException(status_code=404, detail="沒有有效的提交！")

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

@app.post("/process_textreading")
async def reprocess_subject(
    request: SubjectReprocessRequest, 
    token: str = Depends(authenticate_gitlab)
):
    subject_id = request.subject_id
    csv_filename = request.csv_filename
    logger.info(f"開始處理受試者 ID: {subject_id} 的 CSV 檔案：{csv_filename}")

    result = process_text_reading(subject_id, csv_filename)
    return result


# === 主程序入口 ===

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
