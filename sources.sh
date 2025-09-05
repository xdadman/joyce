#!/bin/bash

# Get current date in YYYYMMDD format
current_date=$(date +%Y%m%d)

# Define the folder path
folder_path="export/invertor_monitor_${current_date}"

# Create the directory (including parent directories if they don't exist)
mkdir -p "$folder_path"

# Check if the directory was created successfully
if [ -d "$folder_path" ]; then
    echo "Successfully created folder: $folder_path"
else
    echo "Error: Failed to create folder: $folder_path"
    exit 1
fi

cp *py Dockerfile docker-compose.yml image_build.sh requirements.txt IMAGE* $folder_path
rm $folder_path/config.py
rm $folder_path/flask_server.py


