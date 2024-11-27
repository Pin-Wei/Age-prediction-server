
import requests

url = "http://localhost:7777/get_integrated_result"

# 要發送的數據
print('發送內部請求')
req_data = {
    "subject_id": 'D111111111'
    }

# 設置 headers
headers = {
        "X-GitLab-Token": "tcnl-project",
        "Content-Type": "application/json"
    }

integrated_features = {}

feats = requests.post(url, json=req_data, headers=headers)

print(feats.text)

print('發送成功')