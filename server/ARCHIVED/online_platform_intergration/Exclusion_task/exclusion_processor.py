import os
import pandas as pd

class ExclusionProcessor:
    def __init__(self, input_path, output_path):
        self.input_path = input_path
        self.output_path = output_path
        self.trial_n = 18 * 3

    def create_index(self, data_input, trial_n):
        output = list(data_input.index)
        output.reverse()
        output = output[:trial_n]
        output.reverse()
        return output

    def select_item(self, data_input, trial_n):
        output = data_input.dropna(how='any')
        index = self.create_index(output, trial_n)
        return output.loc[index, :]

    def mean_rt_calculation(self, data_input):
        output = []
        for each in ['s', 'k']:
            value = data_input[data_input.key_resp_keys == each][['key_resp.rt']].values.flatten()
            mean_rt = value.sum() / data_input.shape[0] if data_input.shape[0] > 0 else 0  # Avoid division by zero
            if mean_rt == 0:
                mean_rt = -999  # If Mean_RT is zero, recode as NA value (-999)
            output.append(mean_rt)
        return output

    def rt_calculation_stimulus(self, data_input):
        target = self.mean_rt_calculation(data_input[data_input.stimuli_t == 1])
        non_target = self.mean_rt_calculation(data_input[data_input.stimuli_t == 2])
        new = self.mean_rt_calculation(data_input[data_input.stimuli_t == 3])
        return {'Target': target, 'NonTarget': non_target, 'New': new}

    def rt_calculation_stimulus_cue(self, data_input):
        cue_1 = self.rt_calculation_stimulus(data_input[data_input.number_of_cue_t == 1])
        cue_2 = self.rt_calculation_stimulus(data_input[data_input.number_of_cue_t == 2])
        cue_3 = self.rt_calculation_stimulus(data_input[data_input.number_of_cue_t == 3])
        return {'Cue_1': cue_1, 'Cue_2': cue_2, 'Cue_3': cue_3}

    def rate_calculation_stimulus(self, data_input):
        output = []
        for each in [1, 2, 3]:  # Target/Non-target/New item
            data = data_input[data_input.stimuli_t == each]
            yes_rate = data[data.key_resp_keys == 's'].shape[0] / data.shape[0] if data.shape[0] > 0 else 0
            output.append(yes_rate)
        return output

    def rate_calculation_stimulus_cue(self, data_input):
        output = []
        for each in [1, 2, 3]:  # Cue 1/2/3
            data = data_input[data_input.number_of_cue_t == each]
            yes_rate = self.rate_calculation_stimulus(data)
            output.extend(yes_rate)
        return output

    def process_subject(self, file_path):
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return None

        data = pd.read_csv(file_path)
        data.rename(columns={'key_resp.keys': 'key_resp_keys'}, inplace=True)

        if '指定代號' not in data.columns:
            print(f"Column '指定代號' not found in file: {file_path}")
            return None

        id = data.loc[0, '指定代號']
        data = data[['number_of_cue_t', 'key_resp_keys', 'key_resp.rt', 'stimuli_t']]
        data = self.select_item(data, self.trial_n)

        # Calculate rt and Yes rates
        rt = self.rt_calculation_stimulus_cue(data)
        yes_rate = self.rate_calculation_stimulus_cue(data)
        no_rate = [1 - each for each in yes_rate]
        non_tar_fa = [yes_rate[1], yes_rate[4], yes_rate[7]]
        recollection = [(yes_rate[0] - non_tar_fa[0]), (yes_rate[3] - non_tar_fa[1]), (yes_rate[6] - non_tar_fa[2])]
        familiarity = [non_tar_fa[Each]/(1 - recollection[Each]) if recollection[Each] != 1 else non_tar_fa[Each]/(1 - 0.999) for Each in range(3)]

        output = pd.DataFrame({
            'ID': [id],
            'MEMORY_EXCLUSION_BEH_C1_FAMILIARITY': familiarity[0], 
            'MEMORY_EXCLUSION_BEH_C2_FAMILIARITY': familiarity[1],
            'MEMORY_EXCLUSION_BEH_C3_FAMILIARITY': familiarity[2],
            'MEMORY_EXCLUSION_BEH_C1_RECOLLECTION': recollection[0], 
            'MEMORY_EXCLUSION_BEH_C2_RECOLLECTION': recollection[1],
            'MEMORY_EXCLUSION_BEH_C3_RECOLLECTION': recollection[2],
    # Cue 1 --------------------------------------
            'MEMORY_EXCLUSION_BEH_C1TarHit_PROPORTION': yes_rate[0],
            'MEMORY_EXCLUSION_BEH_C1TarMiss_PROPORTION': no_rate[0],
            'MEMORY_EXCLUSION_BEH_C1NonTarFA_PROPORTION': yes_rate[1],
            'MEMORY_EXCLUSION_BEH_C1NonTarCR_PROPORTION': no_rate[1],
            'MEMORY_EXCLUSION_BEH_C1NewFA_PROPORTION': yes_rate[2],
            'MEMORY_EXCLUSION_BEH_C1NewCR_PROPORTION': no_rate[2],
            'MEMORY_EXCLUSION_BEH_C1TarHit_RT' : rt['Cue_1']['Target'][0],
            'MEMORY_EXCLUSION_BEH_C1TarMiss_RT' : rt['Cue_1']['Target'][1],
            'MEMORY_EXCLUSION_BEH_C1NonTarFA_RT' : rt['Cue_1']['NonTarget'][0],
            'MEMORY_EXCLUSION_BEH_C1NonTarCR_RT' : rt['Cue_1']['NonTarget'][1],
            'MEMORY_EXCLUSION_BEH_C1NewFA_RT' : rt['Cue_1']['New'][0],
            'MEMORY_EXCLUSION_BEH_C1NewCR_RT' : rt['Cue_1']['New'][1],
    # Cue 2 --------------------------------------
            'MEMORY_EXCLUSION_BEH_C2TarHit_PROPORTION': yes_rate[3],
            'MEMORY_EXCLUSION_BEH_C2TarMiss_PROPORTION': no_rate[3],
            'MEMORY_EXCLUSION_BEH_C2NonTarFA_PROPORTION': yes_rate[4],
            'MEMORY_EXCLUSION_BEH_C2NonTarCR_PROPORTION': no_rate[4],
            'MEMORY_EXCLUSION_BEH_C2NewFA_PROPORTION': yes_rate[5],
            'MEMORY_EXCLUSION_BEH_C2NewCR_PROPORTION': no_rate[5],
            'MEMORY_EXCLUSION_BEH_C2TarHit_RT' : rt['Cue_2']['Target'][0],
            'MEMORY_EXCLUSION_BEH_C2TarMiss_RT' : rt['Cue_2']['Target'][1],
            'MEMORY_EXCLUSION_BEH_C2NonTarFA_RT' : rt['Cue_2']['NonTarget'][0],
            'MEMORY_EXCLUSION_BEH_C2NonTarCR_RT' : rt['Cue_2']['NonTarget'][1],
            'MEMORY_EXCLUSION_BEH_C2NewFA_RT' : rt['Cue_2']['New'][0],
            'MEMORY_EXCLUSION_BEH_C2NewCR_RT' : rt['Cue_2']['New'][1],
    # Cue 3 --------------------------------------
            'MEMORY_EXCLUSION_BEH_C3TarHit_PROPORTION': yes_rate[6],
            'MEMORY_EXCLUSION_BEH_C3TarMiss_PROPORTION': no_rate[6],
            'MEMORY_EXCLUSION_BEH_C3NonTarFA_PROPORTION': yes_rate[7],
            'MEMORY_EXCLUSION_BEH_C3NonTarCR_PROPORTION': no_rate[7],
            'MEMORY_EXCLUSION_BEH_C3NewFA_PROPORTION': yes_rate[8],
            'MEMORY_EXCLUSION_BEH_C3NewCR_PROPORTION': no_rate[8],
            'MEMORY_EXCLUSION_BEH_C3TarHit_RT' : rt['Cue_3']['Target'][0],
            'MEMORY_EXCLUSION_BEH_C3TarMiss_RT' : rt['Cue_3']['Target'][1],
            'MEMORY_EXCLUSION_BEH_C3NonTarFA_RT' : rt['Cue_3']['NonTarget'][0],
            'MEMORY_EXCLUSION_BEH_C3NonTarCR_RT' : rt['Cue_3']['NonTarget'][1],
            'MEMORY_EXCLUSION_BEH_C3NewFA_RT' : rt['Cue_3']['New'][0],
            'MEMORY_EXCLUSION_BEH_C3NewCR_RT' : rt['Cue_3']['New'][1]
        })

        return output