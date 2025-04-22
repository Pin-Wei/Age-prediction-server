#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
import requests
import os
import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv
import util

import warnings
from sklearn.exceptions import InconsistentVersionWarning
warnings.filterwarnings("ignore", category=InconsistentVersionWarning)
pd.set_option('future.no_silent_downcasting', True)

class Config:
    def __init__(self):
        self.get_integrated_result_url = os.getenv("GET_INTEGRATED_RESULT_URL")
        self.process_textreading_url = os.getenv("PROCESS_TEXTREADING_URL")
        self.local_headers = {
            "X-GitLab-Token": "tcnl-project",
            "Content-Type": "application/json"
        }
        self.model_path_template = os.path.join(
            "prediction", "model", "<age_abb>") # only trained on behavioral data
        self.scaler_path_template = os.path.join(
            "prediction", "scaler", f"scaler_<age_full>.pkl") # sklearn.preprocessing.MinMaxScaler() object; includes both behavioral and neuroimaging data
        self.percentiles_path_template = os.path.join(
            "prediction", "scaler", f"cognitive_percentiles_<age_full>.pkl")
        self.correction_ref_path_template = os.path.join(
            "prediction", "model", f"<age_abb>_ref.csv")
        self.cognitive_domains = {
            "工作記憶": ["MEMORY_OSPAN_BEH_LETTER_ACCURACY"],
            "情節記憶": [
                "MEMORY_EXCLUSION_BEH_C1_RECOLLECTION",
                "MEMORY_EXCLUSION_BEH_C2_RECOLLECTION",
                "MEMORY_EXCLUSION_BEH_C3_RECOLLECTION"
            ],
            "語言理解":  ["LANGUAGE_SPEECHCOMP_BEH_PASSIVE_ACCURACY"],
            "語言產出": ["LANGUAGE_READING_BEH_NULL_MeanSR"], 
            "動作": []
        }
        self.using_percentile_prediction = True
        self.max_adjustment = 20 # years
        self.brainage_prediction = True
        self.missing_marker = -999 # marked using update_json_result() in server.py
        self.replace_missing_with = 0.5 # since min-max scaler is used
        self.missing_threshold = 0.2
        self.min_percentile = 10
        self.metadata = 412
        self.data = {
            "age": -1,
            "features": {},
            "id_card": "",
            "name": "", 
            "test_date": ""
        }        

def correct_age_with_percentile(config, true_age, prediction, domain_score_list):    
    ## Define the age group and the corresponding median age of the participant
    age_label = pd.cut(
        x=[true_age], 
        bins=[-np.inf, 24, 30, 35, 45, 55, 65, np.inf], 
        labels=['<24', '24-30', '30-35', '35-45', '45-55', '55-65', '>=65']
    )[0]
    median_age = {
        '<24': 20, '24-30': 27.5, '30-35': 32.5, '35-45': 40, '45-55': 50, '55-65': 60, '>=65': 70
    }[str(age_label)]

    ## Calculate weighted domain scores (if valid)
    valid_weighted_scores = []
    for item in domain_score_list:
        if item['score'] != -1:
            valid_weighted_scores.append((50 - item['score']) / 50) 
                # if the score is below average, positively increase the predicted age
                # e.g., if original score is 30, the weighted score is 0.4

    ## Calculate the impact of changes of each domain 
    num_valid = len(valid_weighted_scores)
    if num_valid == 0:
        prediction = median_age
    else:
        impact_per_domain = config.max_adjustment / num_valid 
            # if max_adjustment == 20, increase or decrease a maximum of 20 years
        prediction = median_age + sum(valid_weighted_scores) * impact_per_domain

    corrected_age = prediction 
    corrected_pad = corrected_age - true_age

    return corrected_pad, corrected_age

def correct_age_with_table(config, true_age, prediction):
    age_abb = 'y' if true_age < 40 else 'o'
    correction_ref = pd.read_csv(config.correction_ref_path_template.replace("<age_abb>", age_abb))
    df = (
        pd.DataFrame({
            'real_age': [true_age],
            'pad': [prediction - true_age]
        })
        .assign(
            age_label=lambda x: pd.cut(
                x=x['real_age'], 
                bins=[-1, 24, 30, 35, 45, 55, 65, 100], 
                labels=['<25', '25-30', '30-35', '35-45', '45-55', '55-65', '>=65']
            )
        )
        .assign(
            meanPAD=lambda x: x['age_label'].map(correction_ref.set_index('group')['meanPAD']),
            sdPAD=lambda x: x['age_label'].map(correction_ref.set_index('group')['sdPAD'])
        )
    )
    corrected_pad = (df['pad'].values[0] - df['meanPAD'].values[0]) / df['sdPAD'].values[0]
    corrected_age = np.array(prediction - corrected_pad) 

    return corrected_pad, corrected_age

## ====================================================================================

load_dotenv()
config = Config()

app = Flask(__name__)

@app.route('/predict', methods=['POST'])
def predict():  
    try:        
        ## Receive request from server.py 
        data = request.get_json(force=True)

        if (not data) or ('age' not in data) or ('id_card' not in data) or ('name' not in data) or ('test_date' not in data):
            return jsonify({"error": "Invalid input data"}), 400        
        else:
            config.data.update(data)
            print("\nReceived input data at /predict:")
            print(data)
                 
            try:
                ## Post request to get integrated_result.json via get_integrated_result.py   
                feats = requests.post(
                    url=config.get_integrated_result_url, 
                    headers=config.local_headers, 
                    json={
                        "subject_id": data['id_card']
                    }                    
                )
                print(f"\nPost request to get integrated result...")

                if feats.status_code != 200:
                    print(f"Failed to get integrated result for subject ID: {data['id_card']}")
                    return jsonify({"error": f"HTTP error: {feats.status_code}"}), feats.status_code
                
                else:
                    print(f"Successfully got integrated result for subject ID: {data['id_card']}")
                    result = feats.json()                
                    config.data["features"] = result.get("integrated_result", {})
                
                    ## Get participant's true age
                    true_age = config.data["age"]
                    if true_age == -1: # if age is missing, do not predict brain age
                        config.brainage_prediction = False                    

                    ## Load stored objects according to participant's true age
                    age_abb = 'y' if true_age < 40 else 'o'
                    age_full = 'young' if true_age < 40 else 'old'
                    model = joblib.load(config.model_path_template.replace("<age_abb>", age_abb))
                    scaler = joblib.load(config.scaler_path_template.replace("<age_full>", age_full))             
                    percentiles = joblib.load(config.percentiles_path_template.replace("<age_full>", age_full))

                    print(f"\n受試者真實年齡: {true_age} --> {age_full}\n")

                    ## Define platform features 
                    if hasattr(model, 'feature_names_in_'):
                        platform_features = model.feature_names_in_
                    elif hasattr(model, 'feature_name_'):
                        platform_features = model.feature_name_
                    else:
                        platform_features = util.init_platform_featuress

                    ## Update cognitive domain "動作"
                    config.cognitive_domains["動作"] = [ col for col in platform_features if col.startswith("MOTOR_GOFITTS_BEH") ]

                    ## Prepare dataframe for prediction
                    DF = pd.DataFrame(index=range(1), columns=scaler.feature_names_in_)
                    DF.update(pd.DataFrame([config.data["features"]])) 

                    ## Before scaling, replace missing values with 0
                    data_is_missing = DF == config.missing_marker
                    DF = DF.replace(config.missing_marker, np.nan)
                    DF = DF.fillna(0)

                    ## Apply stored MinMaxScaler(), which scales the dataset between 0 and 1
                    DF_scaled = pd.DataFrame(scaler.transform(DF), columns=scaler.feature_names_in_)

                    ## Fill missing values (that has a field in the JSON data and were used to train the model) 
                    DF_scaled[data_is_missing] = config.replace_missing_with                    

                    ## Calculate the average scores for each cognitive domain
                    domain_score_list = []
                    for cog_domain, features in config.cognitive_domains.items(): 

                        ## Find where the features are missing and calculate the missing ratio 
                        feature_is_missing = data_is_missing[features] 
                        missing_ratio = feature_is_missing.sum(axis=1) / len(features)

                        ## Calculate the average score of the features
                        if missing_ratio.iloc[0] > config.missing_threshold:                             
                            config.brainage_prediction = False                             
                            domain_score_list.append({
                                "name": cog_domain,
                                "score": -1
                            })
                            print(f"Missing data in cognitive domain {cog_domain}")
                            print("Prediction is not possible for this participant.")
                        else:
                            avg_score = DF_scaled[features].mean(axis=1).iloc[0]                            

                            ## Interpolate the average score from (0, 1) to (0, 100)
                            percentile = np.interp(
                                x=avg_score, xp=[0, 1], fp=[0, 100] 
                            )

                            ## Reverse the percentile if the cognitive domain is "動作"
                            if cog_domain == "動作":
                                percentile = 100 - percentile
                                
                            ## Avoid showing too low a score
                            if percentile < config.min_percentile:
                                print(f"Too low a score in cognitive domain {cog_domain}, reset to {config.min_percentile}")
                                percentile = config.min_percentile 
                            
                            domain_score_list.append({
                                "name": cog_domain, 
                                "score": int(round(percentile))
                            })
                            print(f"{cog_domain} percentile: {domain_score_list[-1]['score']}")

                    ## Predict brain-age
                    if config.brainage_prediction:
                        print("\nPredicting brain age...")
                        prediction = float(model.predict(DF_scaled[platform_features])[0])
                        original_pad = prediction - true_age

                        ## Perform brain-age correction 
                        if config.using_percentile_prediction:
                            corrected_pad, corrected_age = correct_age_with_percentile(
                                config, true_age, prediction, domain_score_list
                            )
                        else:
                            corrected_pad, corrected_age = correct_age_with_table(
                                config, true_age, prediction
                            )
                    else:
                        prediction = -1
                        original_pad = -1
                        corrected_pad = -1
                        corrected_age = -1   

                    response = {
                        "id_card": config.data["id_card"],
                        "name": config.data["name"], 
                        "testDate": config.data["test_date"], 
                        "results": {
                            "brainAge": "{:.2f}".format(corrected_age),
                            "chronologicalAge": true_age,
                            "originalPAD": "{:.2f}".format(original_pad),
                            "ageCorrectedPAD": "{:.2f}".format(corrected_pad)
                        },
                        "cognitiveFunctions": domain_score_list,
                        "meta": {
                            "totalParticipants": config.metadata
                        }
                    }
                    print(f"腦齡預測結果: {response['results']['brainAge']}\n")
                    # print(response)

                    return jsonify(response), 200
        
            except requests.RequestException as e:
                print(f"Error: {e}")
                return jsonify({"error": f"\nRequest to get_integrated_result failed: {str(e)}"}), 500

    except Exception as e:
        import traceback
        print("\nUnexpected error during prediction:", str(e))        
        print("Traceback:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500
    
@app.route('/process_textreading', methods=['POST'])
def process_textreading_proxy(): 
    config = Config()
    try:
        ## Receive def process_textreading request
        data = request.get_json(force=True)
        if (not data) or ('subject_id' not in data) or ('csv_filename' not in data):
            return jsonify({"error": "\nMissing required fields while forwarding internal request to process_textreading"}), 400
        
        else:
            print(f"\nReceived input data at /process_textreading: {data}")
            resp = requests.post(
                url=config.process_textreading_url, 
                headers=config.local_headers, 
                json=data
            )      
            if resp.status_code == 200:
                return jsonify({
                        "message": "Successfully forward internal request to process_textreading"
                    }), 200
            else:
                return jsonify({
                        "error": f"Failed to forward internal process_textreading request", 
                        "details": resp.text
                    }), resp.status_code
        
    except Exception as e:
        print("\nUnexpected error while forwarding internal request to process_textreading: ", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("Starting Flask server...")
    app.run(host='0.0.0.0', port=8888)