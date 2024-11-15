#!/bin/bash
# 使用的排程工具是：crontab
# reference: https://blog.gtwang.org/linux/linux-crontab-cron-job-tutorial-and-examples/

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd );
PYTHON_EXE="$SCRIPT_DIR/../.venv/bin/python"
COMMAND="$PYTHON_EXE $SCRIPT_DIR/download_textReading_files.py >> $SCRIPT_DIR/../log_file 2>&1"

case "$1" in
    list) crontab -l;
        ;;
    enable) echo "enable cronjob: $COMMAND"; (crontab -l ; echo "*/2 * * * * $COMMAND") | crontab -
        ;;
    disable) echo "disable cronjob: $COMMAND"; crontab -l | grep -v "$COMMAND"  | crontab -
        ;;
    *) echo "command '$1' unknown"
esac
