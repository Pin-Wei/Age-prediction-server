#!/bin/bash

# crontab: https://blog.gtwang.org/linux/linux-crontab-cron-job-tutorial-and-examples/

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd );
PYTHON_EXE="$SCRIPT_DIR/../venv/bin/python"
LOG_DOWNLOAD_TEXTREADING_FILES="$SCRIPT_DIR/../logs/cronjob_download_textReading_files.log"
LOG_PROCESS_TASKS="$SCRIPT_DIR/../logs/cronjob_process_tasks.log"
COMMAND_DOWNLOAD_TEXTREADING_FILES="$PYTHON_EXE $SCRIPT_DIR/download_textReading_files.py >> $LOG_DOWNLOAD_TEXTREADING_FILES 2>&1"
COMMAND_PROCESS_TASKS="$PYTHON_EXE $SCRIPT_DIR/process_tasks.py >> $LOG_PROCESS_TASKS 2>&1"

case "$1" in
    list) crontab -l;
        ;;
    enable)
        if [ "$2" == "download_textReading_files" ]
        then
            echo "enable cronjob: $COMMAND_DOWNLOAD_TEXTREADING_FILES";
            (crontab -l ; echo "0 */12 * * * $COMMAND_DOWNLOAD_TEXTREADING_FILES") | crontab -
        elif [ "$2" == "process_tasks" ]
        then
            echo "enable cronjob: $COMMAND_PROCESS_TASKS";
            (crontab -l ; echo "*/20 * * * * $COMMAND_PROCESS_TASKS") | crontab -
        else
            echo "service '$2' unknown"
        fi
        ;;
    disable)
        if [ "$2" == "download_textReading_files" ]
        then
            echo "disable cronjob: $COMMAND_DOWNLOAD_TEXTREADING_FILES";
            crontab -l | grep -v "$COMMAND_DOWNLOAD_TEXTREADING_FILES"  | crontab -
        elif [ "$2" == "process_tasks" ]
        then
            echo "disable cronjob: $COMMAND_PROCESS_TASKS";
            crontab -l | grep -v "$COMMAND_PROCESS_TASKS"  | crontab -
        else
            echo "service '$2' unknown"
        fi
        ;;
    *) echo "command '$1' unknown"
esac
