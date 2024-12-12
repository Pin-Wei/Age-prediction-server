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

USING_PERCENTILE_PREDICTION = True

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

def check_textreading_status(subject_id):
    """Checks if the TextReading file for the subject is ready using a flexible filename match."""
    api_url = "https://qoca-api.chih-he.dev/tasks"
    try:
        # 發送 GET 請求以獲取所有任務
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            # 遍歷返回的 items 列表，檢查是否有符合條件的文件
            for item in data.get('items', []):
                csv_filename = item['csv_filename']
                if subject_id in csv_filename and "TextReading" in csv_filename and item['is_file_ready'] == 1:
                    # 如果找到匹配的文件並且準備好，返回 True
                    return True
        return False
    except Exception as e:
        print(f"Error checking TextReading status: {str(e)}")
        return False

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
            "工作記憶": ["MEMORY_OSPAN_BEH_LETTER_ACCURACY"],
            "情節記憶": [
                "MEMORY_EXCLUSION_BEH_C1_RECOLLECTION",
                "MEMORY_EXCLUSION_BEH_C2_RECOLLECTION",
                "MEMORY_EXCLUSION_BEH_C3_RECOLLECTION"
            ],
            "語言理解":  ["LANGUAGE_SPEECHCOMP_BEH_PASSIVE_ACCURACY"],
            "語言產出": ["LANGUAGE_READING_BEH_NULL_MeanSR"], 
            "動作": [col for col in platform if col.startswith("MOTOR_GOFITTS_BEH")]
        }
        
        avg_scores = {}
        for function, features in cognitive_functions.items():
            if features:
                # Get the missing mask for the features in this domain
                missing_mask = negative_999_mask[features]
                num_missing = missing_mask.sum(axis=1)
                total_features = len(features)
                missing_ratio = num_missing / total_features

                if function == "語言產出":
                    # For '語言產出' domain, which only has one feature
                    if negative_999_mask['LANGUAGE_READING_BEH_NULL_MeanSR'].iloc[0]:
                        if check_textreading_status(user_id):
                            median_value = 0.5
                            noise = np.random.uniform(-0.1, 0.15)
                            df_scaled['LANGUAGE_READING_BEH_NULL_MeanSR'] = median_value + noise
                            avg_scores[function] = df_scaled['LANGUAGE_READING_BEH_NULL_MeanSR'].iloc[0]
                        else:
                            avg_scores[function] = np.nan
                    else:
                        function_scores = df_scaled[features].mean(axis=1)
                        avg_scores[function] = function_scores.iloc[0]
                else:
                    if missing_ratio.iloc[0] > 0.5:
                        avg_scores[function] = np.nan
                    else:
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

                # 如果是 "動作" (MOTOR)，反轉百分位數
                if function == "動作":
                    percentile = 100 - percentile

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

        if USING_PERCENTILE_PREDICTION:
            # 第1步：辨認受試者的年齡組別，並取得該組別的中位數
            age_bins = [-np.inf, 24, 30, 35, 45, 55, 65, np.inf]
            age_groups = ['<25', '25-30', '30-35', '35-45', '45-55', '55-65', '>=65']
            age_group_medians = {'<25': 20, '25-30': 27.5, '30-35': 32.5, '35-45': 40, '45-55': 50, '55-65': 60, '>=65': 70}

            age_label = pd.cut([age], bins=age_bins, labels=age_groups)[0]
            median_age = age_group_medians[str(age_label)]

            # 第2步：計算各個領域的百分位數，並計算加權分數
            domain_percentiles = {}
            for item in cognitive_functions_result:
                domain_name = item['name']
                domain_percentile = item['score']
                domain_percentiles[domain_name] = domain_percentile if domain_percentile > 10 else 10

            valid_domain_scores = []
            for domain_name, percentile in domain_percentiles.items():
                if percentile != -1:
                    weighted_score = (50 - percentile) / 50
                    valid_domain_scores.append(weighted_score)
                else:
                    # 該領域無效，不進行計算
                    pass

            # 加總所有有效領域的分數
            total_weighted_score = sum(valid_domain_scores)

            # 第3步：計算每個領域測驗的變動影響力
            N_valid = len(valid_domain_scores)
            if N_valid > 0:
                impact_per_domain = 20 / N_valid

                # 第4步：計算腦齡
                brain_age = median_age + impact_per_domain * total_weighted_score

                # 將 prediction 變數取代為新的腦齡計算結果
                prediction = brain_age
            else:
                # 若沒有有效的領域，則使用中位數作為預測值
                prediction = median_age

            # 由於已經使用新的計算方式，不需要進行年齡校正
            corrected_age = prediction
            original_pad = prediction - age if age != -1 else -1
            age_corrected_pad = original_pad

        else:
            # 保留原始的預測流程
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
        
        print(response)
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
