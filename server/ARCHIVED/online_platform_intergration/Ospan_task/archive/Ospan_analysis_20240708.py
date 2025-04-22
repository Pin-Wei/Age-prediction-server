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
# Math analysis
def Math_analysis(Data_input, Trial_N):
	Output = Data_input[['MathResult']]
	Output = Select_item(Data_input = Output, Trial_N = Trial_N)
	Mean = list(Output.mean()) # get mean

	return(Mean)
# Letter analysis
def Letter_analysis(Data_input, Trial_N):
	Output = Data_input[['LetterResult']]
	Output = Select_item(Data_input = Output, Trial_N = Trial_N)
	Sum = list(Output.sum()) # get mean

	return(Sum)

#--------------------------------------------

# path
Input_path = 'data/'
# string
File_name = 'OnlineTask-OSPAN_Feature.csv'
Feedback = '\n\n\n' + File_name + 'has been saved.\n\n\n'
# value
Trial_N = (4*3)+(6*3)
#===== parameters =====






# Import data -------------------------------
File_list = os.listdir(Input_path)
File_list.remove('Archive')
# Analysis -----------------------------------
ID = list()
Math_result = list()
Letter_result = list()
for i_FileList in File_list:
	Data = pandas.read_csv((Input_path + i_FileList))
# Record ID ----------------------------------
	ID_each = Data.loc[0, '身分證字號']
	ID.append(ID_each)
# Math ---------------------------------------
	Result = Math_analysis(Data_input = Data, Trial_N = Trial_N)
	Math_result.append(Result[0])
# Letter -------------------------------------
	Result = Letter_analysis(Data_input = Data, Trial_N = Trial_N)
	Letter_result.append(Result[0])
# Export data --------------------------------
Output = pandas.DataFrame({'ID': ID, 'MEMORY_OSPAN_BEH_MATH_ACCURACY': Math_result, 'MEMORY_OSPAN_BEH_LETTER_ACCURACY': Letter_result})
Output.to_csv(path_or_buf = File_name, index = False)
print(Feedback)






# quite session
quit()