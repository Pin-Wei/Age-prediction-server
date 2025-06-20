# Cognitive Testing Platform and Brain-Age Prediction Project
This repository provides a fully automated pipeline that downloads and processes behavioral data collected on Pavlovia (an online experimental platform), computes various metrics derived from raw data, and uses them to predict participants' brain age and to calculate how their scores compare with population norms using percentile rankings. The tasks included are *GoFitts*, *Operation Span*, *Speech Comprehension*, *Exclusion*, and *Text Reading*, which span the cognitive domains of *language*, *memory*, and *motion*. Final results are submitted to an external API, and personalized PDF reports are sent to participants via email.

The list of participants and their associated email addresses is stored in CSV format under the `subj_csv_files` directory and uploaded to the external API using the `upload_subj_csv.py` script.

Please note that the underlying database is not publicly available.

# Component Breakdown
### `start.sh`
- Entrypoint script that launches the FastAPI server (`server.py`).
### `server.py`
- Serves the `/webhook` endpoint that listens for webhook events from the Pavlovia GitLab project repositories:
  - When the webhook is triggered by a CSV file upload:
    - Fetch the CSV file into the `../data/<EXPERIMENT_NAME>` directory.
    - If it is **not** from the *TextReading* project:
      - Processes the CSV file with the `TaskIntegrator` object, which calls the appropriate `<EXPERIMENT_NAME>Processor` object defined in a script stored in the `data_processors` directory.
      - Computes task metrics and formats them as a dictionary.
      - Saves (or updates) the result in the participant's JSON file (`<SUBJECT_ID>_integrated_result.json` under the `integrated_results` folder). 
    - If it **is** from the *TextReading* project (since it is the last task, its completion triggers the report generation process):
      - Skip its processing temporarily due to time demands.
      - Send a POST request to the local `/predict` endpoint to trigger the execution of `predict.py`, which returns a JSON data containing predicted brain age and cognitive percentile scores.
      - Send a POST request to `https://qoca-api.chih-he.dev/exams` to upload these results.
      - Send a POST request to `https://qoca-api.chih-he.dev/tasks` to create a report generation task.
- Additionally, it provides the `/report` endpoint.
  - For participants who fail to complete the *TextReading* task, the report generation process needs to be triggered through this approach.
### `cronjob.sh`
- Schedule routine background jobs with the `corntab` command:
  - Execute `process_tasks.py` every **20 minutes**.
  - Execute `download_textReading_files.py` every **12 hours**.
### `download_textReading_files.py`
- Executed periodically by `cronjob.sh`:
  - List the subjects with CSV files and those with WebM audio files, and then compare the two lists to get the list of participants whose WebM audio files have not been downloaded yet.
  - Read CSV files of participants whose WebM audio files have not been downloaded to get their `sessionToken`.
  - Send a GET request to Pavlovia's API (`https://pavlovia.org/api/v2/experiments/<EXPERIMENT_ID>/media`) to get download URLs of their WebM audio files (will return all the media files that have been uploaded; we retrieve specific ones based on participants' `sessionToken`).
  - After downloading the files, send a GET request to the API endpoint `https://qoca-api.chih-he.dev/tasks?csv_filename=< CSV_FILENAME>` to check if the report generation task exists.
  - If the task exists and its `status` is `0`, send a PUT request to the API endpoint `https://qoca-api.chih-he.dev/tasks/<TASK_ID>` to update the `is_file_ready` status from `0` to `1`.
### `process_text_reading.py`
- Serves the `/process_textreading` local endpoint:
  - Process the WebM audio files with the imported `TextReadingProcessor` object and calculate the task metric.
  - Update it in the participant's JSON file (`<SUBJECT_ID>_integrated_result.json`).
### `process_tasks.py`
- Executed periodically by `cronjob.sh`:
  - Send a GET request with query parameters to an external API (`https://qoca-api.chih-he.dev/tasks?is_file_ready=1&status=0`) to search for report generation tasks that need to be processed.
  - For each task, send a POST request to the `/process_textreading` local endpoint to trigger the execution of `process_text_reading.py`.
  - Send a GET request to an external API (`https://qoca-api.chih-he.dev/user/<SUBJECT_ID>`) to retrieve the participant's user info.
  - Send a POST request to the `/predict` local endpoint (re-predict brain age with *TextReading* metric included) and receive a JSON format `predict_result`.
  - Send a PUT request to the API `https://qoca-api.chih-he.dev/tasks/<TASK_ID>` to update `status` to `1`.
  - Send a PUT request to the API `https://qoca-api.chih-he.dev/exams/<EXAM_ID>` to update `predict_result` with `report_status` is `0` to trigger the second PDF report's regeneration.
### `get_integrated_result.py`
- Serves the `/get_integrated_result` local endpoint that returns the content of `<SUBJECT_ID>_integrated_result.json` stored locally.
### `predict.py`
- Serves the `/predict` local endpoint:
  - Assesses participants' data by sending a request to the `/get_integrated_result` local endpoint
  - Loads the appropriate model and scaler by age group.
  - Preprocess input data, calculates cognitive percentile scores for five domains (i.e., *motor*, *working memory*, *language comprehension*, *episodic memory*, and *language production*), and performs brain age prediction with a pre-trained model (stored under the `prediction` folder).
  - Returns results structured in JSON format.
### `util.py`
- Define `PLATFORM_FEATURES`, which stores the name of metrics derived from the cognitive tasks.
### `.env` (hidden)
- Define `GITLAB_TOKEN`, `QOCA_TOKEN`, the name and ID of Pavlovia experiments (`EXPERIMENT_*_NAME` and `EXPERIMENT_*_ID`), as well as the URLs of the local endpoints (`WEBHOOK_URL`, `PROCESS_TEXTREADING_URL`, `GET_INTEGRATED_RESULT_URL`, and `PREDICT_URL`).
