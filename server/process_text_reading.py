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
ALLOWED_PROJECTS = ["ExclusionTask", "GoFitts", "OspanTask", "SpeechComp", "TextReading", "TextReading2025"]
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

def update_json_result(subject_id, result_df):

    # 先處理無效數值
    result_df = result_df.replace([pd.NA, pd.NaT, float('inf'), float('-inf')], -999)
    result_df = result_df.fillna(-999)

    json_file_path = os.path.join(base_path, 'online_platform_intergration', 'integrated_results', f"{subject_id}_integrated_result.json")
    platform_features = util.init_platform_features()
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
    csv_path = DATA_DIR / "TextReading2025" / csv_filename
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
    pattern = f"TextReading2025/{subject_id}_TextReading_{test_date}_recording_mic_*.webm"
    logger.info(f"搜尋音檔的模式: {pattern}")
    audio_files = list(DATA_DIR.glob(pattern))
    
    if not audio_files:
        result["message"] = f"未找到受試者 {subject_id} 在 {test_date} 的任何音頻文件"
        return result
        
    logger.info(f"找到 {len(audio_files)} 個音頻文件供 {subject_id} 處理")
    result["files_processed"] = [f.name for f in audio_files]
    
    text_reading_processor = TextReadingProcessor(
        input_path=DATA_DIR / "TextReading2025",
        output_path=DATA_DIR / "TextReading2025"
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
            print(mean_speech_rate)
            if mean_speech_rate is not None:
                if pd.isna(mean_speech_rate) or mean_speech_rate == float('inf'):
                    mean_speech_rate = -999  # 替換為 JSON 兼容值

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
    uvicorn.run(app, host="0.0.0.0", port=6666)