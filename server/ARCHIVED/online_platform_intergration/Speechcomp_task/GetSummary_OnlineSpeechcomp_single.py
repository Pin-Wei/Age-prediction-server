import pandas as pd
import glob
import os

# Define directories
file_dir = ''
output_dir = ''

# Get subject ID
subject_id = file_dir.split('_')[0]

# Read table
t = pd.read_csv(file_dir)

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

summary = []
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
summary_df.to_csv(os.path.join(output_dir, 'summary_online_speechcomp_'+subject_id+'.csv'), index=False)

print('Done.')