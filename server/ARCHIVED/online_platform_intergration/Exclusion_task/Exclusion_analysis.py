# Import module -----------------------------
import os
import pandas
# Set path to current script ----------------
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
# Print blank lines -------------------------
print('\n')






#===== parameters =====
# define function
# Create index
def Create_index(Data_input, Trial_N):
	Output = list(Data_input.index) # Get row names
	Output.reverse() # Reverse index
	Output = Output[:Trial_N] # Choose index
	Output.reverse() # Reverse index
	
	return Output
# Select item
def Select_item(Data_input, Trial_N):
	Output = Data_input.dropna(how = 'any') # Remove NA values
	Index = Create_index(Data_input = Output, Trial_N = Trial_N) # Create index for selecting items in experiment stage 
	Output = Output.loc[Index, :] # Select item

	return Output
# RT ========================================
# Mean RT calculation
def MeanRT_calculation(Data_input):
	Data = Data_input
	Output = []
	for each in ['s', 'k']:
		Value = Data[Data.key_resp_keys == each][['key_resp.rt']].values.flatten() # Transform data frame to list
		Mean_RT = Value.sum()/Data.shape[0] # Calculate mean RT
		if Mean_RT == 0: # If Mean_RT is zero, recode as NA value (-999)
			Mean_RT = -999
		Output.append(Mean_RT)

	return Output
# RT calculation for stimulus
def RTcalculation_stimulus(Data_input):
	Target = MeanRT_calculation(Data_input = Data_input[Data_input.stimuli_t == 1]) 
	NonTarget = MeanRT_calculation(Data_input = Data_input[Data_input.stimuli_t == 2]) 
	New = MeanRT_calculation(Data_input = Data_input[Data_input.stimuli_t == 3])
	Output = {'Target': Target, 'NonTarget': NonTarget, 'New': New}

	return(Output)
# RT calculation  for stimulus and cue
def RTcalculation_stimulus_cue(Data_input):
	Cue_1 = RTcalculation_stimulus(Data_input = Data_input[Data_input.number_of_cue_t == 1])
	Cue_2 = RTcalculation_stimulus(Data_input = Data_input[Data_input.number_of_cue_t == 2])
	Cue_3 = RTcalculation_stimulus(Data_input = Data_input[Data_input.number_of_cue_t == 3])
	Output = {'Cue_1': Cue_1, 'Cue_2': Cue_2, 'Cue_3': Cue_3}

	return Output
# Rate ======================================
# Yes rate calculation for stimulus
def RateCalculation_stimulus(Data_input):
	Output = list()
	for each in [1, 2, 3]: # Target/Non-target/New item
		Data = Data_input[Data_input.stimuli_t == each]
		Yes_rate = Data[Data.key_resp_keys == 's'].shape[0]/Data.shape[0]
		Output.append(Yes_rate)

	return(Output)
# Yes rate calculation  for stimulus and cue
def RateCalculation_stimulus_cue(Data_input):
	Output = list()
	for each in [1, 2, 3]: # Cue 1/2/3
		Data = Data_input[Data_input.number_of_cue_t == each]
		Yes_rate = RateCalculation_stimulus(Data_input = Data)
		Output.extend(Yes_rate)

	return Output

#--------------------------------------------

# path
Input_path = 'data/'
Output_path = 'feature/'
# string
File_name = 'OnlineTask-EX_Feature.csv'
# value
Trial_N = 18*3
#===== parameters =====






# Import data -------------------------------
File_list = os.listdir(Input_path)
if 'Archive' in File_list:
	File_list.remove('Archive')
# Analysis -----------------------------------
for i_FileList in File_list:
	Data = pandas.read_csv((Input_path + i_FileList))
	Data.rename(columns={'key_resp.keys': 'key_resp_keys'}, inplace = True) # rename variable
# Rearrange data -----------------------------
	ID = Data.loc[0, '指定代號']
	Data = Data[['number_of_cue_t', 'key_resp_keys', 'key_resp.rt', 'stimuli_t']]
	Data = Select_item(Data_input = Data, Trial_N = Trial_N)
# Calculation --------------------------------
	RT = RTcalculation_stimulus_cue(Data_input = Data)
	Yes_rate = RateCalculation_stimulus_cue(Data_input = Data)
	No_rate = [(1 - each) for each in Yes_rate]
# Record rates -------------------------------
	NonTarFA = [Yes_rate[1], Yes_rate[4], Yes_rate[7]]
	RECOLLECTION = [(Yes_rate[0] - NonTarFA[0]), (Yes_rate[3] - NonTarFA[1]), (Yes_rate[6] - NonTarFA[2])]
	FAMILIARITY = [NonTarFA[Each]/(1 - RECOLLECTION[Each]) if RECOLLECTION[Each] != 1 else NonTarFA[Each]/(1 - 0.999) for Each in range(3)]
	Output = pandas.DataFrame({
		'ID': [ID],
		'MEMORY_EXCLUSION_BEH_C1_FAMILIARITY': FAMILIARITY[0], 
		'MEMORY_EXCLUSION_BEH_C2_FAMILIARITY': FAMILIARITY[1],
		'MEMORY_EXCLUSION_BEH_C3_FAMILIARITY': FAMILIARITY[2],
		'MEMORY_EXCLUSION_BEH_C1_RECOLLECTION': RECOLLECTION[0], 
		'MEMORY_EXCLUSION_BEH_C2_RECOLLECTION': RECOLLECTION[1],
		'MEMORY_EXCLUSION_BEH_C3_RECOLLECTION': RECOLLECTION[2],
# Cue 1 --------------------------------------
		'MEMORY_EXCLUSION_BEH_C1TarHit_PROPORTION': Yes_rate[0],
		'MEMORY_EXCLUSION_BEH_C1TarMiss_PROPORTION': No_rate[0],
		'MEMORY_EXCLUSION_BEH_C1NonTarFA_PROPORTION': Yes_rate[1],
		'MEMORY_EXCLUSION_BEH_C1NonTarCR_PROPORTION': No_rate[1],
		'MEMORY_EXCLUSION_BEH_C1NewFA_PROPORTION': Yes_rate[2],
		'MEMORY_EXCLUSION_BEH_C1NewCR_PROPORTION': No_rate[2],
		'MEMORY_EXCLUSION_BEH_C1TarHit_RT' : RT['Cue_1']['Target'][0],
		'MEMORY_EXCLUSION_BEH_C1TarMiss_RT' : RT['Cue_1']['Target'][1],
		'MEMORY_EXCLUSION_BEH_C1NonTarFA_RT' : RT['Cue_1']['NonTarget'][0],
		'MEMORY_EXCLUSION_BEH_C1NonTarCR_RT' : RT['Cue_1']['NonTarget'][1],
		'MEMORY_EXCLUSION_BEH_C1NewFA_RT' : RT['Cue_1']['New'][0],
		'MEMORY_EXCLUSION_BEH_C1NewCR_RT' : RT['Cue_1']['New'][1],
# Cue 2 --------------------------------------
		'MEMORY_EXCLUSION_BEH_C2TarHit_PROPORTION': Yes_rate[3],
		'MEMORY_EXCLUSION_BEH_C2TarMiss_PROPORTION': No_rate[3],
		'MEMORY_EXCLUSION_BEH_C2NonTarFA_PROPORTION': Yes_rate[4],
		'MEMORY_EXCLUSION_BEH_C2NonTarCR_PROPORTION': No_rate[4],
		'MEMORY_EXCLUSION_BEH_C2NewFA_PROPORTION': Yes_rate[5],
		'MEMORY_EXCLUSION_BEH_C2NewCR_PROPORTION': No_rate[5],
		'MEMORY_EXCLUSION_BEH_C2TarHit_RT' : RT['Cue_2']['Target'][0],
		'MEMORY_EXCLUSION_BEH_C2TarMiss_RT' : RT['Cue_2']['Target'][1],
		'MEMORY_EXCLUSION_BEH_C2NonTarFA_RT' : RT['Cue_2']['NonTarget'][0],
		'MEMORY_EXCLUSION_BEH_C2NonTarCR_RT' : RT['Cue_2']['NonTarget'][1],
		'MEMORY_EXCLUSION_BEH_C2NewFA_RT' : RT['Cue_2']['New'][0],
		'MEMORY_EXCLUSION_BEH_C2NewCR_RT' : RT['Cue_2']['New'][1],
# Cue 3 --------------------------------------
		'MEMORY_EXCLUSION_BEH_C3TarHit_PROPORTION': Yes_rate[6],
		'MEMORY_EXCLUSION_BEH_C3TarMiss_PROPORTION': No_rate[6],
		'MEMORY_EXCLUSION_BEH_C3NonTarFA_PROPORTION': Yes_rate[7],
		'MEMORY_EXCLUSION_BEH_C3NonTarCR_PROPORTION': No_rate[7],
		'MEMORY_EXCLUSION_BEH_C3NewFA_PROPORTION': Yes_rate[8],
		'MEMORY_EXCLUSION_BEH_C3NewCR_PROPORTION': No_rate[8],
		'MEMORY_EXCLUSION_BEH_C3TarHit_RT' : RT['Cue_3']['Target'][0],
		'MEMORY_EXCLUSION_BEH_C3TarMiss_RT' : RT['Cue_3']['Target'][1],
		'MEMORY_EXCLUSION_BEH_C3NonTarFA_RT' : RT['Cue_3']['NonTarget'][0],
		'MEMORY_EXCLUSION_BEH_C3NonTarCR_RT' : RT['Cue_3']['NonTarget'][1],
		'MEMORY_EXCLUSION_BEH_C3NewFA_RT' : RT['Cue_3']['New'][0],
		'MEMORY_EXCLUSION_BEH_C3NewCR_RT' : RT['Cue_3']['New'][1]
		})
# Export data --------------------------------
	Export_file = Output_path + ID + '_' + File_name
	Output.to_csv(path_or_buf = Export_file, index = False)
	print(ID + ' ' + 'analyzed.')
print('\n\n\n')






# quite session
quit()