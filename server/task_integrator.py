#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import glob
import pandas as pd

from data_processors.gofitts_processor import GoFittsProcessor
from data_processors.exclusion_processor import ExclusionProcessor
from data_processors.ospan_processor import OspanProcessor
from data_processors.speechcomp_processor import SpeechcompProcessor
from data_processors.textreading_processor import TextReadingProcessor

class TaskIntegrator:
    def __init__(self):
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.base_path, "..", "data")
        self.exp_gofitt_name = os.getenv("EXPERIMENT_GOFITT_NAME")
        self.exp_ospan_name = os.getenv("EXPERIMENT_OSPAN_NAME")
        self.exp_speechcomp_name = os.getenv("EXPERIMENT_SPEECHCOMP_NAME")
        self.exp_exclusion_name = os.getenv("EXPERIMENT_EXCLUSION_NAME")
        self.exp_textreading_name = os.getenv("EXPERIMENT_TEXTREADING_NAME")
        self.exp_name_list = [self.exp_gofitt_name, self.exp_ospan_name, self.exp_speechcomp_name, self.exp_exclusion_name, self.exp_textreading_name]
        
    def find_file(self, directory, subject_id, task_name):
        if task_name == self.exp_textreading_name:
            pattern = f"{subject_id}_TextReading_*.webm"
            files = glob.glob(os.path.join(directory, pattern))
        else:
            patterns = [
                f"{subject_id}_{task_name}_*.csv",
                f"{subject_id}_{task_name.lower()}_*.csv",
                f"{subject_id}_experiment_*.csv", 
                f"{subject_id}_exclusion_*.csv", 
                f"{subject_id}_ospan_*.csv"
            ]
            files = []
            for pattern in patterns:
                matched_files = glob.glob(os.path.join(directory, pattern))
                files.extend(matched_files)        
        if files:
            return files[0]
        else:
            return None

    def process_subject(self, subject_id, tasks_to_process=None):          
        results = []

        if tasks_to_process is None:
            tasks_to_process = self.exp_name_list  

        for task in tasks_to_process:
            processor = {
                self.exp_gofitt_name: GoFittsProcessor(data_dir=os.path.join(self.data_dir, self.exp_gofitt_name)), 
                self.exp_ospan_name: OspanProcessor(data_dir=os.path.join(self.data_dir, self.exp_ospan_name)),
                self.exp_speechcomp_name: SpeechcompProcessor(data_dir=os.path.join(self.data_dir, self.exp_speechcomp_name)),
                self.exp_exclusion_name: ExclusionProcessor(data_dir=os.path.join(self.data_dir, self.exp_exclusion_name)),
                self.exp_textreading_name: TextReadingProcessor(data_dir=os.path.join(self.data_dir, self.exp_textreading_name))
            }.get(task)
            
            if processor is None:
                print(f"No processor found for task: {task}")
                continue

            file_path = self.find_file(processor.data_dir, subject_id, task)            
            if file_path:
                print(f"Processing {task} for subject {subject_id}")
                result = processor.process_subject(file_path)
                if result is not None:
                    results.append(result)
            else:
                print(f"No file found for {task} and subject {subject_id}")

        if not results:
            print(f"No results processed for subject {subject_id}")
            return None

        combined_result = pd.concat(results, axis=1)
        combined_result = combined_result.loc[:, ~combined_result.columns.duplicated()]
        
        return combined_result

def process_and_format_result(result_df, platform_features):
    missing_marker = -999
    formatted_result = { feature: missing_marker for feature in platform_features }

    if result_df is not None:
        ## Updates feature values ​​in the dictionary that are present in the resulting DataFrame
        for feature in platform_features:
            if feature in result_df.columns:
                value = result_df[feature].iloc[0]
                if pd.isna(value):
                    formatted_result[feature] = missing_marker
                else:
                    formatted_result[feature] = value

        ## Dealing with renamed features
        renamed_features = {
            'GOFITTS_BEH_ID0_LeaveTime': 'MOTOR_GOFITTS_BEH_ID1_LeaveTime',
            'GOFITTS_BEH_ID1_LeaveTime': 'MOTOR_GOFITTS_BEH_ID2_LeaveTime',
            'GOFITTS_BEH_ID2_LeaveTime': 'MOTOR_GOFITTS_BEH_ID3_LeaveTime',
            'GOFITTS_BEH_ID3_LeaveTime': 'MOTOR_GOFITTS_BEH_ID4_LeaveTime',
            'GOFITTS_BEH_ID4_LeaveTime': 'MOTOR_GOFITTS_BEH_ID5_LeaveTime',
            'GOFITTS_BEH_ID5_LeaveTime': 'MOTOR_GOFITTS_BEH_ID6_LeaveTime',
            'GOFITTS_BEH_ID0_PointTime': 'MOTOR_GOFITTS_BEH_ID1_PointTime',
            'GOFITTS_BEH_ID1_PointTime': 'MOTOR_GOFITTS_BEH_ID2_PointTime',
            'GOFITTS_BEH_ID2_PointTime': 'MOTOR_GOFITTS_BEH_ID3_PointTime',
            'GOFITTS_BEH_ID3_PointTime': 'MOTOR_GOFITTS_BEH_ID4_PointTime',
            'GOFITTS_BEH_ID4_PointTime': 'MOTOR_GOFITTS_BEH_ID5_PointTime',
            'GOFITTS_BEH_ID5_PointTime': 'MOTOR_GOFITTS_BEH_ID6_PointTime',
            'GOFITTS_BEH_SLOPE_LeaveTime': 'MOTOR_GOFITTS_BEH_SLOPE_LeaveTime',
            'GOFITTS_BEH_SLOPE_PointTime': 'MOTOR_GOFITTS_BEH_SLOPE_PointTime', 
            'SPEECHCOMP_PASSIVE_ACCURACY': 'LANGUAGE_SPEECHCOMP_BEH_PASSIVE_ACCURACY', 
            'SPEECHCOMP_PASSIVE_RT': 'LANGUAGE_SPEECHCOMP_BEH_PASSIVE_RT'
        }        
        for old_key, new_key in renamed_features.items():
            if old_key in result_df.columns:
                value = result_df[old_key].iloc[0]
                if pd.isna(value):
                    formatted_result[new_key] = missing_marker
                else:
                    formatted_result[new_key] = value

    return formatted_result