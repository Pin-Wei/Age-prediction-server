import requests

def test_process_textreading():
    url = 'http://localhost:6666/process_textreading'
    headers = {
        "X-GitLab-Token": "tcnl-project",
        "Content-Type": "application/json"
    }
    json_data = {
        "subject_id": "D111111111",  # Replace with your actual subject ID
        "csv_filename": "D111111111_TextReading_2024-11-26T061845.401Z.csv"  # Replace with your actual CSV filename
    }
    response = requests.post(url=url, json=json_data, headers=headers)
    print(f"Status Code: {response.status_code}")
    try:
        response_data = response.json()
        print(f"Response JSON: {response_data}")
    except ValueError:
        print("Response is not in JSON format.")
        print(f"Response Text: {response.text}")

if __name__ == "__main__":
    test_process_textreading()
