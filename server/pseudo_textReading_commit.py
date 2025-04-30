#!/usr/bin/python

# This script is used to create a pseudo commit from Pavlovia GitLab to local /webhook endpoint.
# python pseudo_textReading_commit.py <subject_id>

import os
import sys
import glob
import requests
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        self.webhook_url = os.getenv("WEBHOOK_URL")
        self.local_headers = {
            "X-GitLab-Token": "tcnl-project", 
            "Content-Type": "application/json"
        }
        self.exp_textreading_name = os.getenv("EXPERIMENT_TEXTREADING_NAME")
        self.exp_textreading_id = os.getenv("EXPERIMENT_TEXTREADING_ID")
        self.source_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.source_dir, "..", "data", self.exp_textreading_name)

## ====================================================================================

if __name__ == "__main__":
    config = Config()

    if len(sys.argv) < 1:
        raise ValueError("Please provide the subject ID as a command line argument.")
    else:
        subj = sys.argv[1]
        csv_filepath = glob.glob(os.path.join(config.data_dir, f"{subj}_*Z.csv"))[0]
        csv_filename = os.path.basename(csv_filepath)
        print(f"csv_filename: {csv_filename}")

        res = requests.post(
            url=config.webhook_url, 
            headers=config.local_headers, 
            json={
                "project": {
                    "id": config.exp_textreading_id, 
                    "name": config.exp_textreading_name
                }, 
                "commits": [{
                    "title": f"data: {csv_filename}", 
                    "author": {"name":"Pavlovia Committer"}, 
                    "added": [f"data/{csv_filename}"], 
                    "note": "a fake commit"
                }]        
            }
        )
        if res.status_code == 200:
            print(f"Successfully generate pseudo TextReading commit for {subj}")
        else:
            raise Exception(f"{res.text}: {res.status_code}")