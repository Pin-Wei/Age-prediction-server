#!/usr/bin/python

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import os
import logging
import json
from dotenv import load_dotenv
from server import authenticate_gitlab

class Config:
    def __init__(self):
        self.source_dir = os.path.dirname(os.path.abspath(__file__))
        self.integrated_results_dir = os.path.join(self.source_dir, "integrated_results")

class SubjectDownloadRequest(BaseModel):
    subject_id: str

## ====================================================================================

load_dotenv()
config = Config()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)  

app = FastAPI(docs_url=None)

@app.post("/get_integrated_result")
async def get_integrated_result(request: SubjectDownloadRequest, token: str = Depends(authenticate_gitlab)):
    subject_id = request.subject_id
    logger.info(f"Received request to get integrated result for subject ID: {subject_id}")
    json_file_path = os.path.join(config.integrated_results_dir, f"{subject_id}_integrated_result.json")

    if not os.path.exists(json_file_path):
        raise HTTPException(status_code=404, detail=f"Integrated result file not found for subject ID: {subject_id}")
    else:
        with open(json_file_path, "r") as f:
            integrated_result = json.load(f)
        return {"status": "ok", "integrated_result": integrated_result}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7777)