# test_predict.py

import requests
import json

# 請確保 Flask 服務已經啟動，並在正確的端口上運行
url = 'http://localhost:8888/predict'

data = {'age': 74, 'id_card': 'U111111111', 'name': '邵嚴萬', 'test_date': '2024-11-28T034511.683Z'}

response = requests.post(url, json=data)

print("Status Code:", response.status_code)
print("Response JSON:")
print(json.dumps(response.json(), ensure_ascii=False, indent=2))
