import os
import pandas as pd

class OspanProcessor:
    def __init__(self, input_path, output_path):
        self.input_path = input_path
        self.output_path = output_path
        self.trial_n = (4*3) + (6*3)

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

    def math_analysis(self, data_input):
        output = data_input[['MathResult']]
        output = self.select_item(output, self.trial_n)
        return output.mean().values[0]

    def letter_analysis(self, data_input):
        output = data_input[['LetterResult']]
        output = self.select_item(output, self.trial_n)
        return output.sum().values[0]

    def process_subject(self, file_path):
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return None

        data = pd.read_csv(file_path)
        id = data.loc[0, '指定代號']
        math_result = self.math_analysis(data)
        letter_result = self.letter_analysis(data)

        output = pd.DataFrame({
            'ID': [id],
            'MEMORY_OSPAN_BEH_MATH_ACCURACY': [math_result],
            'MEMORY_OSPAN_BEH_LETTER_ACCURACY': [letter_result*2.5]
        }) # There are 75 trials in the ospan task, but only 30 trials in the online version. Therefore for the calculation of percentile rank which uses the distribution of "LETTER_COUNT" in quanta feature matrix, the behavioral result (letter_result) of online version is needed to be times 2.5 (30*2.5 = 75) to fit in the "LETTER_COUNT" distribution.

        return output
