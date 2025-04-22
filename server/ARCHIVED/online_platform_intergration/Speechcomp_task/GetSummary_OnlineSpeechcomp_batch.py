import pandas as pd
import glob
import os

# Define directories
data_dir = r'C:\Users\quanta\TCNL Dropbox\tcnl tcnl\Tests\online\speechcomprehension_2022.2.4\data'
output_dir = r'C:\Users\quanta\Dropbox\analysis\language\online_speechcomp'

# Get list of CSV files
file_list = glob.glob(os.path.join(data_dir, '*.csv'))

summary = []

# Loop through each file
for file_path in file_list:
    # Get subject ID
    file_name = os.path.basename(file_path)
    subject_id = file_name.split('_')[0]

    # Read table
    t = pd.read_csv(file_path)

    # Fill NaNs in the 'condition' column with an empty string
    t['condition'] = t['condition'].fillna('')

    # Get condition index
    act = t['condition'].str.contains('action')
    obj = t['condition'].str.contains('object')
    pas = t['condition'].str.contains('passive')

    # Calculate accuracies and reaction times with checks for division by zero
    action_accuracy = (t.loc[act, 'stim_resp.corr'].sum() * 100 / act.sum()) if act.sum() > 0 else float('nan')
    object_accuracy = (t.loc[obj, 'stim_resp.corr'].sum() * 100 / obj.sum()) if obj.sum() > 0 else float('nan')
    passive_accuracy = (t.loc[pas, 'stim_resp.corr'].sum() * 100 / pas.sum()) if pas.sum() > 0 else float('nan')

    action_rt = t.loc[act & (t['stim_resp.corr'] == 1), 'duration'].mean() if (act & (t['stim_resp.corr'] == 1)).sum() > 0 else float('nan')
    object_rt = t.loc[obj & (t['stim_resp.corr'] == 1), 'duration'].mean() if (obj & (t['stim_resp.corr'] == 1)).sum() > 0 else float('nan')
    passive_rt = t.loc[pas & (t['stim_resp.corr'] == 1), 'duration'].mean() if (pas & (t['stim_resp.corr'] == 1)).sum() > 0 else float('nan')

    summary.append({
        'ID': subject_id,
        'ACTION_ACCURACY': action_accuracy,
        'OBJECT_ACCURACY': object_accuracy,
        'PASSIVE_ACCURACY': passive_accuracy,
        'ACTION_RT': action_rt,
        'OBJECT_RT': object_rt,
        'PASSIVE_RT': passive_rt
    })

# Convert summary to DataFrame and save as CSV
summary_df = pd.DataFrame(summary)
summary_df.to_csv(os.path.join(output_dir, 'summary_online_speechcomp.csv'), index=False)

print('Done.')