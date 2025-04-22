import os
import pandas as pd
import numpy as np
import subprocess

class TextReadingProcessor:
    def __init__(self, input_path, output_path):
        self.input_path = input_path
        self.output_path = output_path

    def generate_csv(self, audio_file):
        result = subprocess.run(
            ["/home/tcnl/YHL/Pavloviadata/server/online_platform_intergration/Textreading_Task/whisper_venv/bin/python", 
            "/home/tcnl/YHL/Pavloviadata/server/online_platform_intergration/Textreading_Task/whisper_venv/get_speechrate.py", 
            audio_file],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"Error processing {audio_file}: {result.stderr}")
            return None
        
        # 構造正確的 .words.csv 路徑
        csv_file = str(audio_file).replace(".webm", "_ds.wav.words.csv")
        if os.path.exists(csv_file):
            return csv_file
        else:
            print(f"No .words.csv file generated for {audio_file}")
            return None


    def calculate_mean_syllable_speech_rate(self, csv_files):
        syllable_speech_rates = []

        for csv_file in csv_files:
            try:
                # 只讀取前三列，忽略多餘的列
                df = pd.read_csv(csv_file, encoding='utf-8', usecols=[0, 1, 2], names=['word', 'start', 'end'])
                
                # 計算 syllable speech rate
                df['duration'] = df['end'] - df['start']
                df['word_len'] = df['word'].astype(str).apply(len)
                df['syllable_sr'] = df['word_len'] / df['duration']
                
                # 計算該文件的平均 syllable speech rate
                syllable_sr = df['syllable_sr'].mean()
                syllable_speech_rates.append(syllable_sr)
            except Exception as e:
                print(f"Failed to read or process {csv_file}: {e}")

        if not syllable_speech_rates:
            return None

        # 計算所有文件的平均 syllable speech rate
        mean_syllable_sr = np.mean(syllable_speech_rates)
        return mean_syllable_sr

    def process_subject(self, subject_id):
        # 找到該受試者的所有音頻文件
        audio_files = [f for f in os.listdir(self.input_path) if f.startswith(subject_id) and f.endswith('.webm')]
        
        if not audio_files:
            print(f"No audio files found for subject {subject_id}")
            return None

        csv_files = []
        for audio_file in audio_files:
            file_path = os.path.join(self.input_path, audio_file)
            
            # 生成 .words.csv 文件
            csv_file = self.generate_csv(file_path)
            if csv_file:
                csv_files.append(csv_file)

        if not csv_files:
            print(f"No valid .words.csv files for subject {subject_id}")
            return None

        # 計算平均 syllable speech rate
        mean_speech_rate = self.calculate_mean_syllable_speech_rate(csv_files)

        if mean_speech_rate is None:
            print(f"No valid speech rate calculated for subject {subject_id}")
            return None

        # 將結果保存到 DataFrame
        output = pd.DataFrame({
            'ID': [subject_id],
            'LANGUAGE_READING_BEH_NULL_MeanSR': [mean_speech_rate]
        })

        return output
