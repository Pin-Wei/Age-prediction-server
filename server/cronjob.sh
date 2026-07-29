#!/usr/bin/env bash

# Usage: bash cronjob.sh [enable | disable] [download_textreading_files | process_tasks | upload_to_dropbox]

PYTHON="/home/aclexp/mambaforge/envs/server/bin/python"
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
LOG_DIR="$SCRIPT_DIR/../logs"
CMD_DOWNLOAD_TEXTREADING_FILES="$PYTHON $SCRIPT_DIR/download_textreading_files.py >> $LOG_DIR/cronjob_download_textreading_files.log 2>&1"
CMD_PROCESS_TASKS="$PYTHON $SCRIPT_DIR/process_tasks.py >> $LOG_DIR/cronjob_process_tasks.log 2>&1"
CMD_UPLOAD_DBX="$PYTHON $SCRIPT_DIR/upload_to_dropbox.py >> $LOG_DIR/cronjob_upload_to_dropbox.log 2>&1"

case $1 in
    list) 
		crontab -l
        ;;
		
	clean)
		echo "Delete all current cron jobs ..."
		crontab -r
		;;
		
    enable)
		if [ $2 == "download_textreading_files" ]; then
			cmd="0 */1 * * * $CMD_DOWNLOAD_TEXTREADING_FILES"
			echo "Add cron job: $cmd"
			(crontab -l 2>/dev/null; echo "$cmd") | crontab -
			
		elif [ $2 == "process_tasks" ]; then
			cmd="0 */3 * * * $CMD_PROCESS_TASKS"
			echo "Add cron job: $cmd"
			(crontab -l 2>/dev/null; echo "$cmd") | crontab -
			
		elif [ $2 == "upload_to_dropbox" ]; then
			cmd="0 8 * * 1 $CMD_UPLOAD_DBX"
			echo "Add cron job: $cmd"
			(crontab -l 2>/dev/null; echo "$cmd") | crontab -
		else
            echo "service '$2' unknown"
		fi
		;;
		
    disable)
		if [ $2 == "download_textreading_files" ]; then
			echo "Delete cron jobs with keyword: $CMD_DOWNLOAD_TEXTREADING_FILES"
			crontab -l | grep -v "$CMD_DOWNLOAD_TEXTREADING_FILES" | crontab -
			
		elif [ $2 == "process_tasks" ]; then
			echo "Delete cron jobs with keyword: $CMD_PROCESS_TASKS"
			crontab -l | grep -v "$CMD_PROCESS_TASKS" | crontab -
			
		elif [ $2 == "upload_to_dropbox" ]; then
			echo "Delete cron jobs with keyword: $CMD_UPLOAD_DBX"
			crontab -l | grep -v "$CMD_UPLOAD_DBX" | crontab -
			
		else
            echo "service '$2' unknown"
		fi
		;;
		
	*) echo "command '$1' unknown"
esac

# Example of job definition:
# .---------------- minute (0 - 59)
# |  .------------- hour (0 - 23)
# |  |  .---------- day of month (1 - 31)
# |  |  |  .------- month (1 - 12) OR jan,feb,mar,apr ...
# |  |  |  |  .---- day of week (0 - 6) (Sunday=0 or 7) OR sun,mon,tue,wed,thu,fri,sat
# |  |  |  |  |
# *  *  *  *  * user-name  command to be executed