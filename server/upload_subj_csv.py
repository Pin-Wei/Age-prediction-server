#!/usr/bin/python

import os
import sys
import chardet
import requests

from dotenv import load_dotenv
load_dotenv()

qoca_token = os.getenv("QOCA_TOKEN")
qoca_headers = {
    "Authorization": f"Bearer {qoca_token}"
}

def detect_and_convert_to_utf8(input_path):
    with open(input_path, "rb") as f:
        raw_data = f.read()
    result = chardet.detect(raw_data)
    encoding = result["encoding"]

    if encoding is None:
        raise ValueError("Could not detect encoding")

    if encoding.lower() == "utf-8":
        print("File is already in UTF-8 encoding.")
        return input_path
    else:
        print(f"Detected encoding: {encoding}. Converting to UTF-8...")
        output_path = os.path.splitext(input_path)[0] + "_utf8.csv"
        content = raw_data.decode(encoding, errors="ignore")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        return output_path

def upload_file(file_path):

    if not os.path.exists(file_path):
        raise ValueError(f"File {file_path} does not exist :(")
    
    else:
        print(f"Uploading file: '{file_path}'")
        ext = os.path.splitext(file_path)[1].lower()

        if ext != ".csv":
            raise ValueError(f"Unsupported file type: {ext}")
            
        with open(file_path, 'rb') as f:
            res = requests.post(
                url='https://qoca-api.chih-he.dev/uploadfile', 
                headers=qoca_headers, 
                files={'file': f},
            )
    
    if res.status_code == 200:
        print("Successfully uploaded file :)")
    else:
        print("Failed to upload file :(")
        raise ValueError(f"Failed to upload file: {res.status_code}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        raw_input_path = sys.argv[1]
    else:
        raw_input_path = os.path.join("subj_csv_files", "test_and_NHRI_2025-06-18.csv")

    file_path = detect_and_convert_to_utf8(raw_input_path)    
    upload_file(file_path)