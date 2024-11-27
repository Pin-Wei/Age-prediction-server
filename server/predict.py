# predict_server.py

from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
import os
import joblib
import requests
import json
from datetime import datetime
import util

app = Flask(__name__)

float_formatter = "{:.2f}".format
METADATA = 412

def init_platform_feat():
    platform_features = util.init_platform_featuress

    return platform_features

def get_feature_names(model):
    if hasattr(model, 'feature_names_in_'):
        return model.feature_names_in_
    elif hasattr(model, 'feature_name_'):
        return model.feature_name_
    else:
        return init_platform_feat()

def apply_age_correction(predictions, true_ages, correction_ref):
    corrected_predictions = []
    age_groups = ['<25', '25-30', '30-35', '35-45', '45-55', '55-65', '>=65']
    age_bins = [-1, 24, 30, 35, 45, 55, 65, 100]

    # age_groups = ['<40', '>=40']
    # age_bins = [-1, 39, 100]

    for pred, true_age in zip(predictions, true_ages):
        df = (
            pd.DataFrame({
                'real_age': [true_age],
                'pad': [pred - true_age]
            })
            .assign(
                age_label=lambda x: pd.cut(x['real_age'], bins=age_bins, labels=age_groups)
            )
            .assign(
                meanPAD=lambda x: x['age_label'].map(correction_ref.set_index('group')['meanPAD']),
                sdPAD=lambda x: x['age_label'].map(correction_ref.set_index('group')['sdPAD'])
            )
        )

        if df['meanPAD'].isna().values[0] or df['sdPAD'].isna().values[0]:
            corrected_predictions.append(pred)
            continue

        padac = (df['pad'].values[0] - df['meanPAD'].values[0]) / df['sdPAD'].values[0]
        corrected_pred = pred - padac
        corrected_predictions.append(corrected_pred)
    return np.array(corrected_predictions)

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json(force=True)
        if not data or 'age' not in data or 'id_card' not in data or 'name' not in data or 'test_date' not in data:
            return jsonify({"error": "Invalid input data"}), 400

        print(data)

        # API 端點 URL
        print('正在取得數據')
        url = "http://localhost:7777/get_integrated_result"

        # 要發送的數據
        print('發送內部請求')
        req_data = {
            "subject_id": data['id_card']
        }

        # 設置 headers
        headers = {
            "X-GitLab-Token": "tcnl-project",
            "Content-Type": "application/json"
        }

        integrated_features = {}

        try:
            feats = requests.post(url, json=req_data, headers=headers)
            print('發送成功')
            
            if feats.status_code == 200:
                result = feats.json()
                print("整合特徵成功:")
                print(json.dumps(result, indent=2))
                integrated_features = result.get("integrated_result", {})
            elif feats.status_code == 404:
                return jsonify({"error": f"無法找到 subject ID: {data['id_card']} 的整合結果"}), 404
            else:
                print(f"錯誤: HTTP {feats.status_code}")
                print(feats.text)
                return jsonify({"error": f"整合特徵失敗: HTTP {feats.status_code}"}), feats.status_code

        except requests.RequestException as e:
            print(f"請求錯誤: {e}")
            return jsonify({"error": f"請求錯誤: {str(e)}"}), 500

        default_data = {
            "age": -1,
            "features": integrated_features,
            "id_card": "",
            "name": "",
            "test_date": ""
        }
        
        default_data.update(data)
        
        age = default_data["age"]
        features = default_data["features"]
        user_id = default_data["id_card"]
        user_name = default_data["name"]
        test_date = default_data["test_date"]
        
        age_abb = 'y' if age < 40 else 'o'
        age_full = 'young' if age < 40 else 'old'

        model_full_path = os.path.join('./prediction/model', f'{age_abb}')
        model = joblib.load(model_full_path)
        scaler = joblib.load(f'./prediction/scaler/scaler_{age_full}.pkl')
                
        all_features = scaler.feature_names_in_
        df = pd.DataFrame([features])
        df_full = pd.DataFrame(index=range(1), columns=all_features)
        df_full.update(df)
        
        negative_999_mask = df_full == -999
        df_full = df_full.replace(-999, np.nan)
        
        df_full = df_full.fillna(0)
        df_scaled = pd.DataFrame(scaler.transform(df_full), columns=all_features)
        
        df_scaled[negative_999_mask] = 0.5

        platform = get_feature_names(model)
        
        cognitive_functions = {
            "工作記憶": ["MEMORY_OSPAN_BEH_LETTER_COUNT", "MEMORY_OSPAN_BEH_MATH_ACCURACY"],
            "情節記憶": [col for col in platform if col.startswith("MEMORY_EXCLUSION_BEH")],
            "語言理解": ["LANGUAGE_SPEECHCOMP_BEH_PASSIVE_ACCURACY", "LANGUAGE_SPEECHCOMP_BEH_PASSIVE_RT"],
            "語言產出": ["LANGUAGE_READING_BEH_NULL_MeanSR"], 
            "動作": [col for col in platform if col.startswith("MOTOR_GOFITTS_BEH")]
        }
        
        avg_scores = {}
        for function, features in cognitive_functions.items():
            if features:
                function_scores = df_scaled[features].mean(axis=1)
                avg_scores[function] = function_scores.iloc[0]
            else:
                avg_scores[function] = np.nan
        
        percentiles = joblib.load(f'./prediction/scaler/cognitive_percentiles_{age_full}.pkl')
        print("Percentile data columns:", percentiles.columns)
        
        cognitive_functions_result = []
        for function in cognitive_functions.keys():
            if function in avg_scores and not np.isnan(avg_scores[function]):
                percentile_values = percentiles[function].sort_values().values
                percentile = np.interp(avg_scores[function], [0, 1], [0, 100])
                cognitive_functions_result.append({
                    "name": function,
                    "score": int(round(percentile))
                })
            else:
                cognitive_functions_result.append({
                    "name": function,
                    "score": -1
                })
        
        prediction = float(model.predict(df_scaled[platform])[0]) if age != -1 else -1
        corrected_age = float(apply_age_correction(
            predictions=[prediction],
            true_ages=[age],
            correction_ref=pd.read_csv(f'./prediction/model/{age_abb}_ref.csv')
        )[0]) if age != -1 else -1
        
        original_pad = prediction - age if age != -1 else -1
        age_corrected_pad = corrected_age - age if age != -1 else -1
        
        response = {
            "id_card": user_id,
            "name": user_name,
            "testDate": test_date,
            "results": {
                "brainAge": float_formatter(corrected_age) if age != -1 else "-1",
                "chronologicalAge": age,
                "originalPAD": float_formatter(original_pad) if age != -1 else "-1",
                "ageCorrectedPAD": float_formatter(age_corrected_pad) if age != -1 else "-1"
            },
            "cognitiveFunctions": cognitive_functions_result,
            "meta": {
                "totalParticipants": METADATA
            }
        }
        
        return jsonify(response), 200
    
    except Exception as e:
        print("Error during prediction:", str(e))
        import traceback
        print("Traceback:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/process_textreading', methods=['POST'])
def process_textreading_proxy():
    try:
        data = request.get_json(force=True)
        if not data or 'subject_id' not in data or 'csv_filename' not in data:
            return jsonify({"error": "Missing required fields"}), 400

        # Forward the request to the internal server.py
        internal_url = 'http://localhost:8000/process_textreading'
        headers = {
            "X-GitLab-Token": "tcnl-project",
            "Content-Type": "application/json"
        }
        
        # Forward the request
        response = requests.post(
            url=internal_url,
            json=data,
            headers=headers
        )
        
        # Return 200 immediately after successful forwarding
        if response.status_code == 200:
            return jsonify({"message": "Request forwarded successfully"}), 200
        else:
            return jsonify({
                "error": "Internal processing failed",
                "details": response.text
            }), response.status_code

    except Exception as e:
        print("Error forwarding request:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("Starting Flask server...")
    app.run(host='0.0.0.0', port=8888)