#!/usr/bin/python

# This script is used to create a pseudo commit from Pavlovia GitLab to local /webhook endpoint.
# python pseudo_commit.py <project_no> <csv_filename>

import os
import sys
import glob
import requests
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        self.source_dir = os.path.dirname(os.path.abspath(__file__))
        self.webhook_url = os.getenv("WEBHOOK_URL")
        self.local_headers = {
            "X-GitLab-Token": "tcnl-project", 
            "Content-Type": "application/json"
        }
        self.exp_gofitt_name      = os.getenv("EXPERIMENT_GOFITT_NAME")
        self.exp_ospan_name       = os.getenv("EXPERIMENT_OSPAN_NAME")
        self.exp_speechcomp_name  = os.getenv("EXPERIMENT_SPEECHCOMP_NAME")
        self.exp_exclusion_name   = os.getenv("EXPERIMENT_EXCLUSION_NAME")
        self.exp_textreading_name = os.getenv("EXPERIMENT_TEXTREADING_NAME")
        self.exp_gofitt_id        = os.getenv("EXPERIMENT_GOFITT_ID")
        self.exp_ospan_id         = os.getenv("EXPERIMENT_OSPAN_ID")
        self.exp_speechcomp_id    = os.getenv("EXPERIMENT_SPEECHCOMP_ID")
        self.exp_exclusion_id     = os.getenv("EXPERIMENT_EXCLUSION_ID")
        self.exp_textreading_id   = os.getenv("EXPERIMENT_TEXTREADING_ID")

## ====================================================================================

if __name__ == "__main__":
    config = Config()

    if len(sys.argv) < 2:
        raise ValueError(
            "Please provide the project number (1-5) and the csv filename as a command line argument." + 
            "Go to https://gitlab.pavlovia.org/tcnl-quanta/<project_name>/-/commits/master to get the csv filename."
        )
    elif sys.argv[1] not in ["1", "2", "3", "4", "5"]:
        raise ValueError(
            "Please provide the project number first." + 
            "[1]: gofitt, [2]: ospan, [3]: speechcomp, [4]: exclusion, [5]: textreading"
        )
    else:
        project_no = sys.argv[1]
        project_id = {
            "1": config.exp_gofitt_id, 
            "2": config.exp_ospan_id, 
            "3": config.exp_speechcomp_id, 
            "4": config.exp_exclusion_id, 
            "5": config.exp_textreading_id
        }[project_no]
        project_name = {
            "1": config.exp_gofitt_name, 
            "2": config.exp_ospan_name, 
            "3": config.exp_speechcomp_name, 
            "4": config.exp_exclusion_name, 
            "5": config.exp_textreading_name
        }[project_no]

        # subj = sys.argv[2]
        # csv_filepath = glob.glob(os.path.join(
        #     config.source_dir, "..", "data", project_name, f"{subj}_*Z.csv"
        # ))[0]
        # csv_filename = os.path.basename(csv_filepath)
        # print(f"csv_filename: {csv_filename}")
        csv_filename = sys.argv[2]

        res = requests.post(
            url=config.webhook_url, 
            headers=config.local_headers, 
            json={
                "project": {
                    "id": project_id, 
                    "name": project_name
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
            print(f"Successfully generate pseudo {project_name} commit for {csv_filename}")
            print(":-)")
        else:
            raise Exception(f"{res.text}: {res.status_code}")