# Cognitive testing platform and brain-age prediction project
This repository implements a fully automated pipeline that processes behavioral data collected from Pavlovia (an online experimental platform), computes various metrics derived from five cognitive tasks (i.e., *GoFitts*, *Operation Span*, *Speech Comprehension*, *Exclusion*, and *Text Reading*; spanning *language*, *memory*, and *motion* domains), and uses them to predict participants' brain age and to determine how their scores rank in the population using percentile values. These results are submitted to an external API, and the final reports are sent to participants via email in PDF format. 
The list of participants and their email addresses is maintained in CSV format under the `subj_csv_files` directory and uploaded to the external API using the `upload_subj_csv.py` script.
Please note that the underlying database is not publicly available.

## Component Breakdown
### `start.sh`
- Entrypoint script that launches the FastAPI server (`server.py`).
### `server.py`
- Serves the `/webhook` endpoint that listens for webhook events from the Pavlovia GitLab project repos:
  - When the webhook is triggered by the upload of a CSV file.
    - Fetch the CSV file to the `../data/<EXPERIMENT_NAME>` directory.
    - If it is **not** from the *TextReading* project:
      - Processes the CSV file with the `TaskIntegrator` object, which calls the corresponding `<EXPERIMENT_NAME>Processor` object defined in a script stored in the `data_processors` directory.
      - After task metrics are computed, format them as a dictionary.
      - Saves (or updates) the result into a JSON file (`<SUBJECT_ID>_integrated_result.json`; stored under the `integrated_results` folder). 
    - If it **is** from the *TextReading* project (since it is the last task, its completion triggers the report generation process):
      - Skip its processing (for now, because it takes time).
      - Send a POST request to the `/predict` local endpoint to trigger the execution of `predict.py` and receive a JSON data containing predicted brain age and cognitive percentile scores.
      - Send a POST request to an external API (`https://qoca-api.chih-he.dev/exams`) to upload these results.
      - Send a POST request to an external API (`https://qoca-api.chih-he.dev/tasks`) to create a report generation task.
- Additionally, it provides the `/report` local endpoint.
  - For participants who fail to complete the *TextReading* task, the report generation process needs to be triggered through this approach.
### `cronjob.sh`
- Set up  schedule with the `corntab` command:
  - Execute `process_tasks.py` every **20 minutes**.
  - Execute `download_textReading_files.py` every **12 hours**.
### `download_textReading_files.py`
- Executed periodically by `cronjob.sh`:
  - 
### `process_text_reading.py`
- Serves the `/process_textreading` local endpoint:
  - 
### `process_tasks.py`
- 
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
