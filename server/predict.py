#!/usr/bin/python

from flask import Flask, request, jsonify
import requests
import os
import json
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
import util

app = Flask(__name__)

@app.route('/predict', methods=['POST'])
def predict():
    try:
        USING_PERCENTILE_PREDICTION = True
        BRAINAGE_PREDICTION = True
        MISSING_MARKER = -999 # marked using update_json_result() in server.py
        MISSING_THRESHOLD = 0.2
        MIN_PERCENTILE = 10 
        METADATA = 412

        ## Receive request from server.py 
        data = request.get_json(force=True)
        if (not data) or ('age' not in data) or ('id_card' not in data) or ('name' not in data) or ('test_date' not in data):
            return jsonify({"error": "Invalid input data"}), 400
        else:
            print(data)

        ## Post request to get JSON data via get_integrated_result.py
        url = "http://localhost:7777/get_integrated_result"
        headers = {
            "X-GitLab-Token": "tcnl-project",
            "Content-Type": "application/json"
        }
        req_data = {
            "subject_id": data['id_card']
        }
        integrated_result = {}
        try:
            feats = requests.post(url, json=req_data, headers=headers)
            print(f"Post request to get integrated result...")

            if feats.status_code == 200:
                result = feats.json()
                print(json.dumps(result, indent=2))
                integrated_result = result.get("integrated_result", {})
                print("Successfully got integrated result")
            elif feats.status_code == 404:
                return jsonify({"error": f"Failed to get integrated result for subject ID: {data['id_card']}"}), 404
            else:
                return jsonify({"error": f"HTTP error:{feats.status_code}"}), feats.status_code
        
        except requests.RequestException as e:
            print(f"Error: {e}")
            return jsonify({"error": f"Request failed: {str(e)}"}), 500

        ## Parse data as variables
        default_data = {
            "age": -1,
            "features": integrated_result,
            "id_card": "",
            "name": "", 
            "test_date": ""
        }
        default_data.update(data)

        true_age = default_data["age"]
        if true_age == -1:
            BRAINAGE_PREDICTION = False

        ## Load stored objects according to participant's age
        age_abb = 'y' if true_age < 40 else 'o'
        age_full = 'young' if true_age < 40 else 'old'

        model = joblib.load(os.path.join("prediction", "model", f"{age_abb}"))
            # only trained on behavioral data
        scaler = joblib.load(os.path.join("prediction", "scaler", f"scaler_{age_full}.pkl")) 
            # sklearn.preprocessing.MinMaxScaler() object
            # includes both behavioral and neuroimaging data
        percentiles = joblib.load(os.path.join("prediction", "scaler", f"cognitive_percentiles_{age_full}.pkl"))
        correction_ref = pd.read_csv(os.path.join("prediction", "model", f"{age_abb}_ref.csv"))

        ## Prepare dataframe for prediction
        all_features = scaler.feature_names_in_ 
        df_full = pd.DataFrame(index=range(1), columns=all_features)
        df = pd.DataFrame([default_data["features"]])
        df_full.update(df) 

        ## Missing values that has a field in the JSON data (= were used to train the model) 
        data_is_missing = df_full == MISSING_MARKER
        df_full = df_full.replace(MISSING_MARKER, np.nan).infer_objects(copy=False)
        df_full = df_full.fillna(0)

        ## Apply stored MinMaxScaler(), which scales the dataset between 0 and 1
        df_scaled = pd.DataFrame(scaler.transform(df_full), columns=all_features)

        ## Fill missing values (that has a field in the JSON data and were used to train the model) with 0.5 
        df_scaled[data_is_missing] = 0.5

        ## Define platform features 
        if hasattr(model, 'feature_names_in_'):
            platform_features = model.feature_names_in_
        elif hasattr(model, 'feature_name_'):
            platform_features = model.feature_name_
        else:
            platform_features = util.init_platform_featuress

        ## Define the mapping between (certain) platform features and cognitive cog_domains
        cognitive_domains = {
            "工作記憶": ["MEMORY_OSPAN_BEH_LETTER_ACCURACY"],
            "情節記憶": [
                "MEMORY_EXCLUSION_BEH_C1_RECOLLECTION",
                "MEMORY_EXCLUSION_BEH_C2_RECOLLECTION",
                "MEMORY_EXCLUSION_BEH_C3_RECOLLECTION"
            ],
            "語言理解":  ["LANGUAGE_SPEECHCOMP_BEH_PASSIVE_ACCURACY"],
            "語言產出": ["LANGUAGE_READING_BEH_NULL_MeanSR"], 
            "動作": [col for col in platform_features if col.startswith("MOTOR_GOFITTS_BEH")]
        }

        ## Calculate the average scores for each cognitive domain
        avg_scores = {}
        for cog_domain, features in cognitive_domains.items(): 

            ## Find where the features are missing and calculate the missing ratio 
            feature_is_missing = data_is_missing[features] 
            missing_ratio = feature_is_missing.sum(axis=1) / len(features)

            ## Calculate the average score of the features
            if missing_ratio.iloc[0] > MISSING_THRESHOLD: # if the percentage of missing values is greater than specified threshold
                avg_scores[cog_domain] = np.nan           # set the average score to NaN
                BRAINAGE_PREDICTION = False               # and mark that prediction is not possible
            else:
                avg_scores[cog_domain] = df_scaled[features].mean(axis=1).iloc[0]

        domain_score_list = []
        for cog_domain in cognitive_domains.keys():
            if cog_domain in avg_scores.keys() and not np.isnan(avg_scores[cog_domain]):
                percentile = np.interp(avg_scores[cog_domain], [0, 1], [0, 100])

                if cog_domain == "動作": 
                    percentile = 100 - percentile # reverse the percentile

                if percentile < MIN_PERCENTILE:
                    percentile = MIN_PERCENTILE # avoid showing too low a score
                    
                domain_score_list.append({
                    "name": cog_domain, 
                    "score": int(round(percentile))
                })
            else:
                domain_score_list.append({
                    "name": cog_domain,
                    "score": -1
                })

        ## Predict brain-age
        if BRAINAGE_PREDICTION:
            prediction = float(model.predict(df_scaled[platform_features])[0])
        else:
            prediction = -1

        ## Perform brain-age correction
        if prediction != -1: 
            original_pad = prediction - true_age

            if USING_PERCENTILE_PREDICTION: 
                # corrected_pad = original_pad

                ## Define the age group and the corresponding median age of the participant
                age_bins = [-np.inf, 24, 30, 35, 45, 55, 65, np.inf]
                age_groups = ['<24', '24-30', '30-35', '35-45', '45-55', '55-65', '>=65']
                age_group_medians = {'<24': 20, '24-30': 27.5, '30-35': 32.5, '35-45': 40, '45-55': 50, '55-65': 60, '>=65': 70}

                age_label = pd.cut([true_age], bins=age_bins, labels=age_groups)[0]
                median_age = age_group_medians[str(age_label)]

                ## Calculate the sum of (weighted) valid domain scores
                valid_domain_scores = []
                for item in domain_score_list:
                    domain_name = item['name']
                    domain_percentile = item['score'] 

                    if domain_percentile != -1:
                        weighted_score = (50 - domain_percentile) / 50
                        valid_domain_scores.append(weighted_score)

                total_weighted_score = sum(valid_domain_scores)

                ## Calculate the impact of changes of each domain
                N_valid = len(valid_domain_scores)
                if N_valid > 0:
                    impact_per_domain = 20 / N_valid # why 20?
                    prediction = median_age + impact_per_domain * total_weighted_score
                else:
                    prediction = median_age

                corrected_age = prediction 
                corrected_pad = corrected_age - true_age

            else: # Use brain-age correction table

                age_groups = ['<25', '25-30', '30-35', '35-45', '45-55', '55-65', '>=65']
                age_bins = [-1, 24, 30, 35, 45, 55, 65, 100]
                df = (
                    pd.DataFrame({
                        'real_age': [true_age],
                        'pad': [prediction - true_age]
                    })
                    .assign(
                        age_label=lambda x: pd.cut(x['real_age'], bins=age_bins, labels=age_groups)
                    )
                    .assign(
                        meanPAD=lambda x: x['age_label'].map(correction_ref.set_index('group')['meanPAD']),
                        sdPAD=lambda x: x['age_label'].map(correction_ref.set_index('group')['sdPAD'])
                    )
                )
                corrected_pad = (df['pad'].values[0] - df['meanPAD'].values[0]) / df['sdPAD'].values[0]
                corrected_age = np.array(prediction - corrected_pad)
        else:
            original_pad = -1
            corrected_pad = -1
            corrected_age = -1

        response = {
            "id_card": default_data["id_card"],
            "name": default_data["name"], 
            "testDate": default_data["test_date"], 
            "results": {
                "brainAge": "{:.2f}".format(corrected_age),
                "chronologicalAge": true_age,
                "originalPAD": "{:.2f}".format(original_pad),
                "ageCorrectedPAD": "{:.2f}".format(corrected_pad)
            },
            "cognitiveFunctions": domain_score_list,
            "meta": {
                "totalParticipants": METADATA
            }
        }
        print(response)
        return jsonify(response), 200
    
    except Exception as e:
        print("Unexpected error during prediction:", str(e))
        import traceback
        print("Traceback:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500
    
@app.route('/process_textreading', methods=['POST'])
def process_textreading_proxy():
    try:
        data = request.get_json(force=True)
        if (not data) or ('subject_id' not in data) or ('csv_filename' not in data):
            return jsonify({"error": "Missing required fields"}), 400
        
        url = 'http://localhost:8000/process_textreading'
        headers = {
            "X-GitLab-Token": "tcnl-project",
            "Content-Type": "application/json"
        }
        resp = requests.post(url=url, json=data, headers=headers)

        if resp.status_code == 200:
            return jsonify({"message": "Successfully forward internal request to process_textreading"}), 200
        else:
            return jsonify({
                    "error": f"Failed to forward internal process_textreading request", 
                    "details": resp.text
                }), resp.status_code
        
    except Exception as e:
        print("Unexpected error while forwarding internal request to process_textreading: ", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("Starting Flask server...")
    app.run(host='0.0.0.0', port=8888)