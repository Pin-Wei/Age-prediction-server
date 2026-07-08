#!/usr/bin/env python

# This script reads the predicted_results.json and integrated_results.json files of all participants, and then organizes them into a table
# The script also executes patches.py if any subject_id is specified as an argument

# Usage: python tidy_predicted_results.py [-rp] [-s <subject_id1> <subject_id2> ...]

import os
import re
import json
import glob
import argparse
import subprocess
import numpy as np
import pandas as pd

from server import Config, setup_logger, predict

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--subjects", nargs="*", default=[],
                        help="Subject IDs that need patches to be executed.")
    parser.add_argument("-rp", "--re_predict", action="store_true", 
                        help="Reproduce predicted results for all subjects.")
    return parser.parse_args()

def get_all_subject_ids():
    '''
    Scans the "integrated_results" directory to find all unique subject IDs
    that match the expected pattern ("????s????-?" where each ? is a digit). 
    '''
    subject_ids = set()
    for fp in glob.glob(os.path.join("integrated_results", "*.json")):
        subject_id = os.path.basename(fp).split("_")[0]
        if re.match(r"[\d]{4}s[\d]{4}-[\d]{1}", subject_id): 
            subject_ids.add(subject_id)

    return sorted(subject_ids)

def get_prediction_results(subject_id, args, config, logger):
    '''
    Retrieves the prediction results for a given subject ID, 
    and extracts the necessary fields to be organized into a dictionary, 
    which will later be converted into a DataFrame.
    
    If "re_predict" is True, it will call the predict function to get the results. 
    Otherwise, it will read from the existing JSON file.
    '''
    def _get_test_date(subject_id, config):
        '''
        Scans the data directory for files matching the subject ID 
        and extracts the test date from the filename.
        
        To get the most recent test date,
        the files are checked in reverse order of the execution of the experiments.        
        '''
        for exp in config.exp_name_list[::-1]: 
            fp = glob.glob(os.path.join(config.data_dir, exp, f"{subject_id}_*Z.csv"))
            if fp:
                return os.path.basename(fp[0]).split("_")[2].split(".")[0]

    def _orginize_results(subject_id, data):
        '''
        Extracts the necessary fields from the JSON data
        and organizes them into a dictionary.
        '''
        scores = { 
            item["name"]: item["score"] for item in data["cognitiveFunctions"] 
        }
        results = {
            "Date": data["testDate"], 
            "SID": subject_id.split("-")[0], 
            "Session": subject_id.split("-")[1],
            "Name": data["name"], 
            "Age": data["results"]["chronologicalAge"],
            "Brain Age": data["results"]["brainAge"],
            "PAD": data["results"]["originalPAD"],
            "Corrected PAD": data["results"]["ageCorrectedPAD"]
        }
        results.update(scores)
        results["Avg"] = np.mean(list(scores.values())) if not any(v == -1 for v in scores.values()) else -1
        return results
        
    if args.re_predict:
        test_date = _get_test_date(subject_id, config)
        data = predict(subject_id, config, logger, test_date)
    else:
        fp = os.path.join("predicted_results", f"{subject_id}_predicted_result.json")
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)

    if data is None:
        logger.warning(f"No predicted results found for {subject_id}")
        print("\nBefore continuing, please check if the uploaded subject_id is correct.\nExiting for now ...\n")
        exit(1)
        return {}
    else: 
        return _orginize_results(subject_id, data)

def get_integrated_results(subject_id):
    '''
    Retrieves the integrated results for a given subject ID,
    and returns a dictionary of the results, 
    where any value of -999 is replaced with NaN.
    '''
    fp = os.path.join("integrated_results", f"{subject_id}_integrated_result.json")
    with open(fp, "r", encoding="utf-8") as f:
        data = json.load(f)

    return {
        k: v if v != -999 else np.nan 
        for k, v in data.items()
    }

def main():
    config = Config()
    logger = setup_logger()  
    args = parse_args()

    subject_ids = get_all_subject_ids()
    data_rows = []

    for subject_id in subject_ids:
        ## Executing patches.py if specified:
        if subject_id in args.subjects:
            subprocess.run(["python", "patches.py", subject_id])

        results = get_prediction_results(subject_id, args, config, logger)
        platform_features = get_integrated_results(subject_id)    
        results.update(platform_features)    
        data_row = pd.DataFrame(results, index=[0])
        data_rows.append(data_row)

    df = pd.concat(data_rows, ignore_index=True)

    ## Saving the DataFrame to a CSV file:
    out_path = os.path.join("predicted_results", "tidy_predicted_results.csv")
    df = df.sort_values(by="Date")
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\n{len(data_rows)} results are organized into a table and saved to:\n{out_path}\n")

if __name__ == "__main__":
    main()