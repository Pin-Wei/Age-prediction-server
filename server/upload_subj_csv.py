#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import requests
import pandas as pd

from dotenv import load_dotenv
load_dotenv()

qoca_token = os.getenv("QOCA_TOKEN")
qoca_headers = {
    "Authorization": f"Bearer {qoca_token}"
}


def load_subj_csv(file_path: str, encoding_types: list[str] = ["utf-8", "cp950", "big5"]):
    for encoding in encoding_types:
        try:
            df = pd.read_csv(file_path, dtype=str, encoding=encoding)
            if encoding == "utf-8":
                return (df, False)
            else:
                print("Converting to UTF-8 ...")
                return (df, True)

        except UnicodeDecodeError:
            continue
    
    raise ValueError(f"Cannot decode {file_path} as any of {encoding_types}")


def confirm_date_format(df: pd.DataFrame, date_col: str = "出生年月日"):
    if pd.api.types.is_datetime64_any_dtype(df[date_col]):
        return (df, False)
    else:
        print("Correcting date format ...")
        serials = pd.to_numeric(df[date_col], errors="coerce")
        restored = pd.to_datetime(serials, unit="D", origin="1899-12-30")
        df[date_col] = df[date_col].mask(serials.notna(), restored.dt.strftime("%m/%d/%Y"))
        return (df, True)


def upload_file(file_path: str):
    print("Uploading file ...")
        
    with open(file_path, 'rb') as f:
        res = requests.post(
            url='https://qoca-api.chih-he.dev/uploadfile', 
            headers=qoca_headers, 
            files={'file': f},
        )
    
    if res.status_code == 200:
        print("Successfully uploaded file :)")
    else:
        raise ValueError(f"Failed to upload file '{file_path}': {res.status_code}")


def test_user_ids(file_path: str, id_col: str = "身分證字號"):
    df = pd.read_csv(file_path, encoding="utf-8")
    subj_ids = df[id_col][-5:]
    print(f"Testing last {len(subj_ids)} user IDs ...")

    failed_ids = [
        sid for sid in subj_ids
        if requests.get(url=f"https://qoca-api.chih-he.dev/user/{sid}").status_code != 200
    ]
    if failed_ids:
        raise ValueError(f"\nFailed to retrieve user info for following IDs:\n{failed_ids}")
    else:
        print(f"All user IDs can be retrieved from the API.")
        

def main(file_name: str):
    file_path = os.path.join("subj_csv_files", file_name)
    assert os.path.exists(file_path), f"File {file_path} does not exist :("

    stem, ext = os.path.splitext(file_path)
    assert ext == ".csv", "Input file must be in CSV format."

    df, encoding_changed = load_subj_csv(file_path)
    df, date_format_changed = confirm_date_format(df)

    if encoding_changed or date_format_changed:
        file_path = f"{stem.rstrip('+')}+{ext}"
        df.to_csv(file_path, index=False, encoding="utf-8", lineterminator="\r\n")
        print(f"Saved new file: {os.path.basename(file_path)}")
    
    upload_file(file_path)
    test_user_ids(file_path)


if __name__ == "__main__":
    print()
    main(sys.argv[1])
    print("\nDone!\n")