#!/usr/bin/python

# This script is used to create a pseudo commit from Pavlovia GitLab to local /webhook endpoint.
# python pseudo_commit.py

import os
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

config = Config()

csv_name = "B000000000-1_TextReading_2025-04-16T072513.874Z.csv"
payload = {
        "project": {
            "id": config.exp_textreading_id, 
            "name": config.exp_textreading_name
        }, 
        "commits": [{
            "title": f"data: {csv_name}", 
            "author": {"name":"Pavlovia Committer"}, 
            "added": [f"data/{csv_name}"]
        }]        
    }

res = requests.post(
    url=config.webhook_url, 
    headers=config.local_headers, 
    json=payload
)

print(f"Status code: {res.status_code}")
print(res.text)
