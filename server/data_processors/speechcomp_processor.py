import os
import pandas as pd

class SpeechcompProcessor:
    def __init__(self, data_dir):
        self.data_dir = data_dir

    def process_subject(self, file_path):
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return None

        # Read table
        t = pd.read_csv(file_path)

        # Get subject ID
        subject_id = os.path.basename(file_path).split('_')[0]

        # Fill NaNs in the 'condition' column with an empty string
        t['condition'] = t['condition'].fillna('')

        # Get condition index
        act = t['condition'].str.contains('action')
        obj = t['condition'].str.contains('object')
        pas = t['condition'].str.contains('passive')

        # Calculate accuracies and reaction times with checks for division by zero
        # action_accuracy = (t.loc[act, 'stim_resp.corr'].sum() * 100 / act.sum()) if act.sum() > 0 else float('nan')
        # object_accuracy = (t.loc[obj, 'stim_resp.corr'].sum() * 100 / obj.sum()) if obj.sum() > 0 else float('nan')
        passive_accuracy = (t.loc[pas, 'stim_resp.corr'].sum() * 100 / pas.sum()) if pas.sum() > 0 else float('nan')

        # action_rt = t.loc[act & (t['stim_resp.corr'] == 1), 'duration'].mean() if (act & (t['stim_resp.corr'] == 1)).sum() > 0 else float('nan')
        # object_rt = t.loc[obj & (t['stim_resp.corr'] == 1), 'duration'].mean() if (obj & (t['stim_resp.corr'] == 1)).sum() > 0 else float('nan')
        passive_rt = t.loc[pas & (t['stim_resp.corr'] == 1), 'duration'].mean() if (pas & (t['stim_resp.corr'] == 1)).sum() > 0 else float('nan')

        output = pd.DataFrame({
            'ID': [subject_id],
            'SPEECHCOMP_PASSIVE_ACCURACY': [passive_accuracy],
            'SPEECHCOMP_PASSIVE_RT': [passive_rt]
        })

        return output