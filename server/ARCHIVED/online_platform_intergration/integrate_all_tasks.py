import os
import glob
import pandas as pd
import json
from online_platform_intergration.Exclusion_task.exclusion_processor import ExclusionProcessor
from online_platform_intergration.Ospan_task.ospan_processor import OspanProcessor
from online_platform_intergration.Speechcomp_task.speechcomp_processor import SpeechcompProcessor
from online_platform_intergration.Textreading_Task.textreading_processor import TextReadingProcessor

class GoFittsProcessor:
    def __init__(self, input_path, output_path):
        """
        初始化 GoFittsProcessor

        :param input_path: 輸入資料的路徑
        :param output_path: 輸出資料的路徑
        """
        self.input_path = input_path
        self.output_path = output_path

    def process_subject(self, file_path):
        """
        處理單個受試者的 GoFitts 資料

        :param file_path: 受試者資料檔案的路徑
        :return: 處理後的 DataFrame，或 None 如果檔案不存在
        """
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return None
        
        df = pd.read_csv(file_path)
        # 確保 ID 欄位名稱為 '指定代號'
        df = df.rename(columns={'ID': '指定代號'})
        return df

class TaskIntegrator:
    def __init__(self, base_path):
        data_path = os.path.join(base_path, '..', 'data')
        print(f"Data path: {data_path}")
        self.exclusion_processor = ExclusionProcessor(
            input_path=os.path.join(data_path, 'ExclusionTask_ElderVersion'),
            output_path=os.path.join(base_path, 'online_platform_intergration', 'Exclusion_task', 'feature')
        )
        self.ospan_processor = OspanProcessor(
            input_path=os.path.join(data_path, 'OspanTask'),
            output_path=os.path.join(base_path, 'online_platform_intergration', 'Ospan_task', 'feature')
        )
        self.speechcomp_processor = SpeechcompProcessor(
            input_path=os.path.join(data_path, 'SpeechComp'),
            output_path=os.path.join(base_path, 'online_platform_intergration', 'Speechcomp_task', 'feature')
        )
        self.gofitts_processor = GoFittsProcessor(
            input_path=os.path.join(data_path, 'GoFitts'),
            output_path=os.path.join(base_path, 'online_platform_intergration', 'GoFitts_task', 'feature')
        )
        self.textreading_processor = TextReadingProcessor(
            input_path=os.path.join(data_path, 'TextReading2025'),
            output_path=os.path.join(base_path, 'online_platform_intergration', 'TextReading_task', 'feature')
        )

    def find_file(self, directory, subject_id, task_name):
        """
        在指定目錄中尋找符合條件的檔案

        :param directory: 目錄路徑
        :param subject_id: 受試者 ID
        :param task_name: 任務名稱
        :return: 找到的檔案路徑，或 None 如果未找到
        """
        files = []
        if task_name == 'GoFitts':
            pattern = f"GoFitts-{subject_id}-summary.csv"
            files = glob.glob(os.path.join(directory, pattern))
        elif task_name == 'TextReading2025':
            pattern = f"{subject_id}_TextReading_*.webm"
            files = glob.glob(os.path.join(directory, pattern))
        else:
            patterns = [
                f"{subject_id}_{task_name}_*.csv",
                f"{subject_id}_{task_name.lower()}_*.csv",
                f"{subject_id}_experiment_*.csv",
                f"{subject_id}_ospan_*.csv"
            ]
            for pattern in patterns:
                matched_files = glob.glob(os.path.join(directory, pattern))
                files.extend(matched_files)
        
        if files:
            return files[0]
        return None

    def process_subject(self, subject_id, tasks_to_process=None):
        if tasks_to_process is None:
            tasks_to_process = ['exclusion', 'OspanTask', 'SpeechComp', 'GoFitts', 'TextReading']
        
        results = []

        task_processor_mapping = {
            'exclusion': self.exclusion_processor,
            'OspanTask': self.ospan_processor,
            'SpeechComp': self.speechcomp_processor,
            'GoFitts': self.gofitts_processor,
            'TextReading': self.textreading_processor
        }

        for task in tasks_to_process:
            processor = task_processor_mapping.get(task)
            if processor is None:
                print(f"No processor found for task: {task}")
                continue

            file = self.find_file(processor.input_path, subject_id, task)
            if file:
                print(f"Processing {task} for subject {subject_id}")
                result = processor.process_subject(file)
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
    """
    處理並格式化結果，確保包含所有平台特徵

    :param result_df: 處理後的 DataFrame
    :param platform_features: 平台特徵列表
    :return: 格式化後的結果字典
    """
    # 創建一個包含所有平台特徵的字典，初始值為 -999
    formatted_result = {feature: -999 for feature in platform_features}
    
    # 更新字典中存在於結果 DataFrame 中的特徵值
    if result_df is not None:
        for feature in platform_features:
            if feature in result_df.columns:
                value = result_df[feature].iloc[0]
                if pd.isna(value):
                    formatted_result[feature] = -999
                else:
                    formatted_result[feature] = value
        
        # 處理 GoFitts 特徵的命名差異
        gofitts_mapping = {
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
            'GOFITTS_BEH_SLOPE_PointTime': 'MOTOR_GOFITTS_BEH_SLOPE_PointTime'
        }
        
        for old_key, new_key in gofitts_mapping.items():
            if old_key in result_df.columns:
                value = result_df[old_key].iloc[0]
                if pd.isna(value):
                    formatted_result[new_key] = -999
                else:
                    formatted_result[new_key] = value
        
        # 處理 SpeechComp 特徵的命名差異
        if 'SPEECHCOMP_PASSIVE_ACCURACY' in result_df.columns:
            value = result_df['SPEECHCOMP_PASSIVE_ACCURACY'].iloc[0]
            if pd.isna(value):
                formatted_result['LANGUAGE_SPEECHCOMP_BEH_PASSIVE_ACCURACY'] = -999
            else:
                formatted_result['LANGUAGE_SPEECHCOMP_BEH_PASSIVE_ACCURACY'] = value
        if 'SPEECHCOMP_PASSIVE_RT' in result_df.columns:
            value = result_df['SPEECHCOMP_PASSIVE_RT'].iloc[0]
            if pd.isna(value):
                formatted_result['LANGUAGE_SPEECHCOMP_BEH_PASSIVE_RT'] = -999
            else:
                formatted_result['LANGUAGE_SPEECHCOMP_BEH_PASSIVE_RT'] = value

    return formatted_result
