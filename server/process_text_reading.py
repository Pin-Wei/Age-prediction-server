#!/usr/bin/python

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel
import requests
import uvicorn

import os
import glob
import logging
import pandas as pd
from dotenv import load_dotenv

import util
from server import authenticate_gitlab, update_json_result
from data_processors.textreading_processor import TextReadingProcessor

app = FastAPI(docs_url=None)

class Config:
    def __init__(self):
        self.source_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.source_dir, "..", "data")
        self.integrated_results_dir = os.path.join(self.source_dir, "integrated_results")
        self.predict_url = os.getenv("PREDICT_URL")  
        self.fetch_file_url = "https://gitlab.pavlovia.org/api/v4/projects/{}/repository/files/data%2F{}/raw?ref=master"
        self.gitlab_token = os.getenv("GITLAB_TOKEN")
        self.gitlab_headers = {
            "Authorization": f"Bearer {self.gitlab_token}",
        }
        self.local_headers = {
            "X-GitLab-Token": "tcnl-project",
            "Content-Type": "application/json"
        }
        self.qoca_headers = {
            "Content-Type": "application/json"
        }
        self.exp_textreading_name = os.getenv("EXPERIMENT_TEXTREADING_NAME")
        self.platform_features = util.init_platform_features
        self.missing_marker = -999

class SubjectReprocessRequest(BaseModel):
    subject_id: str
    csv_filename: str 

def process_text_reading(subject_id: str, csv_filename: str, config, logger) -> dict:
    result = {
        "status": "error",
        "message": "",
        "files_processed": [],
        "mean_speech_rate": None,
        "success": False,
        "csv_filename": csv_filename
    }    
    csv_path = os.path.join(config.data_dir, config.exp_textreading_name, csv_filename)
    
    if not os.path.exists(csv_path):
        result["message"] = f"CSV file not found: {csv_filename}"
        return result
    else:        
        try:
            df = pd.read_csv(csv_path)
            test_date = df['date'].iloc[0]  # e.g., 2024-10-29_11h04.28.020
            logger.info(f"Test date from CSV: {test_date}")
            
            pattern = f"{subject_id}_TextReading_{test_date}_recording_mic_*.webm"
            audio_files = list(glob.glob(os.path.join(config.data_dir, config.exp_textreading_name, pattern)))

            if not audio_files:
                result["message"] = f"No audio files found for subject {subject_id} on date {test_date}"
                return result
            else:
                logger.info(f"Found {len(audio_files)} audio files for subject {subject_id} on date {test_date}")
                result["files_processed"] = [ os.path.basename(f) for f in audio_files ]

                csv_files = []
                for audio_file in audio_files:
                    logger.info(f"Processing audio file: {audio_file}")
                    try:
                        csv_file = TextReadingProcessor().generate_csv(audio_file)
                        if csv_file:
                            csv_files.append(csv_file)
                    except Exception as e:
                        logger.error(f"Error processing audio file {audio_file}: {str(e)}")

                if csv_files:
                    try:
                        mean_speech_rate = TextReadingProcessor().calculate_mean_syllable_speech_rate(csv_files)

                        if mean_speech_rate is None:
                            result["message"] = "Failed to calculate mean speech rate. "
                        elif pd.isna(mean_speech_rate) or mean_speech_rate == float('inf'):
                            mean_speech_rate = config.missing_marker
                        else:
                            logger.info(f"Mean speech rate for subject {subject_id}: {mean_speech_rate}")
                            result.update({
                                "status": "success",
                                "message": "Successfully processed audio files and calculated mean speech rate.",
                                "mean_speech_rate": mean_speech_rate,
                                "success": True
                            })
                            result_df = pd.DataFrame({
                                'ID': [subject_id],
                                'LANGUAGE_READING_BEH_NULL_MeanSR': [mean_speech_rate]
                            })
                            update_json_result(subject_id, result_df, config, logger)
                            
                    except Exception as e:
                        result["message"] = f"Error in calculating mean speech rate: {str(e)}"
                else:
                    result["message"] = f"No CSV files generated for subject {subject_id}"
                    return result
                
        except Exception as e:
            result["message"] = f"Failed to read CSV file: {str(e)}"
            return result

@app.post("/process_textreading")
async def reprocess_subject(request: SubjectReprocessRequest, token: str = Depends(authenticate_gitlab)):
    subject_id = request.subject_id
    csv_filename = request.csv_filename    
    logger.info(f"Starting to process CSV file for subject ID: {subject_id} with filename: {csv_filename}")
    result = process_text_reading(subject_id, csv_filename, config, logger)
    return result

if __name__ == "__main__":
    load_dotenv()
    config = Config()

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)  

    uvicorn.run(app, host="0.0.0.0", port=6666)