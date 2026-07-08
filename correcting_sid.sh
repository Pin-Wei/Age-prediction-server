#!/bin/bash

# As noted in /media/data2/pinwei/Age_pred_server/server/subj_csv_files/notes.txt
# the data collection team made some typos when entering the subject_id(s).
# This script is for correcting and standardizing file names.

APPLY=false
echo ""

while getopts ":y" opt; do
    case "$opt" in
        y) 
			APPLY=true 
			;;
        *)
            echo "Usage: $0 [-y] OLD_PATTERN NEW_PATTERN"
            exit 1
            ;;
    esac
done

shift $((OPTIND - 1))

OLD=$1
NEW=$2

if [ -z "$OLD" ] || [ -z "$NEW" ]; then
    echo "Error: missing arguments"
    echo "Usage: $0 OLD_PATTERN NEW_PATTERN"
    exit 1
fi

if ! $APPLY; then 
	echo "Planning to but not yet rename the following files: "
fi

find . -type f -name "*$OLD*" | while IFS= read -r file; do
    dir="$(dirname "$file")"
    base="$(basename "$file")"
    newbase="${base//$OLD/$NEW}"
	
    if $APPLY; then
        mv -v -- "$file" "$dir/$newbase"
    else
        echo "$file -> $dir/$newbase"
    fi
done

if ! $APPLY; then 
	echo ""
	echo "If you wish to rename the files, please use: $0 [-y] OLD_PATTERN NEW_PATTERN"
fi

echo ""