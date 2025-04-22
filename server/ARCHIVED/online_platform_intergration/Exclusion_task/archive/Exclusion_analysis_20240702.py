# Import module -----------------------------
import os
import pandas
# Set path to current script ----------------
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)






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
# Yes rate calculation
def YesRate_calculation(Data_input):
	Output = list()
	for each in [1, 2, 3]:
		Data = Data_input[Data_input.stimuli_t == each] # Target/Non-target/New item
		Yes_rate = Data[Data.key_resp_keys == 's'].shape[0]/Data.shape[0]
		Output.append(Yes_rate)

	return(Output)
# Rate calculation
def Rate_calculation(Data_input):
	Output = list()
	for each in [1, 2, 3]:
		Data = Data_input[Data_input.number_of_cue_t == each] # Cue 1/2/3
		Yes_rate = YesRate_calculation(Data_input = Data)
		for eeach in Yes_rate:
			Output.append(eeach)

	return Output

#--------------------------------------------

# path
Input_path = 'data/'
# string
File_name = 'OnlineTask-EX_Feature.csv'
Feedback = '\n\n\n' + File_name + 'has been saved.\n\n\n'
# value
Trial_N = 18*3
#===== parameters =====






# Import data -------------------------------
File_list = os.listdir(Input_path)
File_list.remove('Archive')
# Analysis -----------------------------------
ID = list()
TargetHit_C1 = list()
TargetHit_C2 = list()
TargetHit_C3 = list()
TargetMiss_C1 = list()
TargetMiss_C2 = list()
TargetMiss_C3 = list()
NonTargetFA_C1 = list()
NonTargetFA_C2 = list()
NonTargetFA_C3 = list()
NonTargetCR_C1 = list()
NonTargetCR_C2 = list()
NonTargetCR_C3 = list()
NewItemFA_C1 = list()
NewItemFA_C2 = list()
NewItemFA_C3 = list()
NewItemCR_C1 = list()
NewItemCR_C2 = list()
NewItemCR_C3 = list()
Recollection_C1 = list()
Recollection_C2 = list()
Recollection_C3 = list()
for i_FileList in File_list:
	Data = pandas.read_csv((Input_path + i_FileList))
	Data.rename(columns={'key_resp.keys': 'key_resp_keys'}, inplace = True) # rename variable
# Record ID ----------------------------------
	ID_each = Data.loc[0, '身分證字號']
	ID.append(ID_each)
# Rate calculation ---------------------------
	Data = Data[['number_of_cue_t', 'key_resp_keys', 'stimuli_t']]
	Data = Select_item(Data_input = Data, Trial_N = Trial_N)
	Yes_rate = Rate_calculation(Data_input = Data)
	No_rate = [(1 - each) for each in Yes_rate]
# Recode yes rates ---------------------------
	TargetHit_C1.append(Yes_rate[0])
	NonTargetFA_C1.append(Yes_rate[1])
	NewItemFA_C1.append(Yes_rate[2])
	TargetHit_C2.append(Yes_rate[3])
	NonTargetFA_C2.append(Yes_rate[4])
	NewItemFA_C2.append(Yes_rate[5])
	TargetHit_C3.append(Yes_rate[6])
	NonTargetFA_C3.append(Yes_rate[7])
	NewItemFA_C3.append(Yes_rate[8])
# Recode no rates ----------------------------
	TargetMiss_C1.append(No_rate[0])
	NonTargetCR_C1.append(No_rate[1])
	NewItemCR_C1.append(No_rate[2])
	TargetMiss_C2.append(No_rate[3])
	NonTargetCR_C2.append(No_rate[4])
	NewItemCR_C2.append(No_rate[5])
	TargetMiss_C3.append(No_rate[6])
	NonTargetCR_C3.append(No_rate[7])
	NewItemCR_C3.append(No_rate[8])
# Recode recollection ------------------------
	Recollection_C1.append(Yes_rate[0] - Yes_rate[1])
	Recollection_C2.append(Yes_rate[3] - Yes_rate[4])
	Recollection_C3.append(Yes_rate[6] - Yes_rate[7])
# Export data --------------------------------
Output = pandas.DataFrame({
	'ID': ID, 
	'MEMORY_EXCLUSION_BEH_C1_RECOLLECTION': Recollection_C1, 
	'MEMORY_EXCLUSION_BEH_C2_RECOLLECTION': Recollection_C2,
	'MEMORY_EXCLUSION_BEH_C3_RECOLLECTION': Recollection_C3,
	'MEMORY_EXCLUSION_BEH_C1TarHit_PROPORTION': TargetHit_C1,
	'MEMORY_EXCLUSION_BEH_C1TarMiss_PROPORTION': TargetMiss_C1,
	'MEMORY_EXCLUSION_BEH_C1NonTarFA_PROPORTION': NonTargetFA_C1,
	'MEMORY_EXCLUSION_BEH_C1NonTarCR_PROPORTION': NonTargetCR_C1,
	'MEMORY_EXCLUSION_BEH_C1NewFA_PROPORTION': NewItemFA_C1,
	'MEMORY_EXCLUSION_BEH_C1NewCR_PROPORTION': NewItemCR_C1,
	'MEMORY_EXCLUSION_BEH_C2TarHit_PROPORTION': TargetHit_C2,
	'MEMORY_EXCLUSION_BEH_C2TarMiss_PROPORTION': TargetMiss_C2,
	'MEMORY_EXCLUSION_BEH_C2NonTarFA_PROPORTION': NonTargetFA_C2,
	'MEMORY_EXCLUSION_BEH_C2NonTarCR_PROPORTION': NonTargetCR_C2,
	'MEMORY_EXCLUSION_BEH_C2NewFA_PROPORTION': NewItemFA_C2,
	'MEMORY_EXCLUSION_BEH_C2NewCR_PROPORTION': NewItemCR_C2,
	'MEMORY_EXCLUSION_BEH_C3TarHit_PROPORTION': TargetHit_C3,
	'MEMORY_EXCLUSION_BEH_C3TarMiss_PROPORTION': TargetMiss_C3,
	'MEMORY_EXCLUSION_BEH_C3NonTarFA_PROPORTION': NonTargetFA_C3,
	'MEMORY_EXCLUSION_BEH_C3NonTarCR_PROPORTION': NonTargetCR_C3,
	'MEMORY_EXCLUSION_BEH_C3NewFA_PROPORTION': NewItemFA_C3,
	'MEMORY_EXCLUSION_BEH_C3NewCR_PROPORTION': NewItemCR_C3
	})
Output.to_csv(path_or_buf = File_name, index = False)
print(Feedback)






# quite session
quit()