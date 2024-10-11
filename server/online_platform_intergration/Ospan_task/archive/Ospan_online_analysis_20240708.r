# make a blink line
cat("\n", fill = TRUE)



##### parameters #####
# define function
# create ID
create_ID <- function(subject_number)
	{
	for (i in 1:length(subject_number))
		{
		number_of_zeros <- (4 - nchar(as.integer(subject_number[i])))
		zeros <- NULL
		if (number_of_zeros != 0)
			{
			for (j in 1:number_of_zeros)
				{
				zeros <- paste(zeros, "0", sep = "")
				}		
			}
		subject_number[i] <- paste("PAV", "-", zeros, as.character(subject_number[i]), sep = "")
		}
	return(subject_number)
	}
# recode variable
recode_variable <- function(Data)
	{
	number_of_item_in_each_block <- na.omit(raw_data$study_phase_loop.thisRepN)[1:length_of_practice*(-1)] + 1
	# recode Result_of_math
	Data$Result_of_math <- 100 + number_of_item_in_each_block*10 + Data$Result_of_math
	# recode Result_of_letter
	Data$Result_of_letter <- 200 + number_of_item_in_each_block*10 + Data$Result_of_letter
	return(Data)
	}
# analysis
analysis <- function(Data)
	{
	# number of total correct trials of math
	correct_trial_math <- sum(na.omit(raw_data$MathResult)[1:length_of_practice*(-1)])
	result_data <- correct_trial_math
	# number of total correct trials of letter
	correct_trial_letter <- sum(na.omit(raw_data$LetterResult)[1:length_of_practice*(-1)])
	result_data <- c(result_data, correct_trial_letter)
	# ratio of total correct trials of math
	result_data <- c(result_data, correct_trial_math/75)
	# ration of total correct trials of letter
	result_data <- c(result_data, correct_trial_letter/75)
	# accuracy
	# math 
	for (i in 1:length(number_of_item_in_each_letter_order))
		{
		factor <- 100 + i*10 + 1
		requirement <- Data$Result_of_math == factor
		result_data <- c(result_data, length(Data$Result_of_math[requirement == TRUE])/number_of_item_in_each_letter_order[i])
		}
	# letter
	for (i in 1:length(number_of_item_in_each_letter_order))
		{
		factor <- 200 + i*10 + 1
		requirement <- Data$Result_of_letter == factor
		result_data <- c(result_data, length(Data$Result_of_letter[requirement == TRUE])/number_of_item_in_each_letter_order[i])
		} 
	# duration of math
	result_data <- c(result_data, Data$Duration_of_math[1])
	result_data <- round(result_data, digits = 3)
	return(result_data)
	}
# export file
export_file <- function(Data, export_path, export_file_name)
	{
	export_file <- paste(export_path, "/", export_file_name, sep = "")
	write.csv(Data, export_file, row.names = FALSE, na = " ")
	cat(export_file, fill = TRUE)
	}
length_of_practice <- 9
number_of_item_in_each_letter_order <- c(15, 15, 15, 12, 9, 6, 3)
ana_import_path <- "../../../beh/online_experiment/ana"
raw_data_import_path <- "../../../beh/online_experiment/raw_data"
export_path <- "../../../beh/online_experiment"
file_name <- "Ospan_online.csv"
result_file_name <- "Ospan_online_result.csv"
##### parameters #####



# specify subject number
subject_number <- c(16, 17)



# create ID
subject_number <- create_ID(subject_number)
# import online esult data
online_result <- read.csv(paste(ana_import_path, "/", result_file_name, sep = ""))
# file list in raw data folder
file_list <- list.files(raw_data_import_path)
for (i in file_list)
	{
	# choose raw data
	file_list_split <- strsplit(i, "_")
	requirement <- file_list_split[[1]][1] %in% subject_number
	if (requirement == TRUE)
		{
		import_file <- paste(raw_data_import_path, "/", i, sep = "")
		# import raw data
		raw_data <- read.csv(import_file)
		
		######################################################################################################################################################################
		
		# data arrangement
		Data <- data.frame(
							# remove white space in ID
							ID = gsub(" ", "", raw_data$受試者編號, fixed = TRUE),
							Loadings = raw_data$LOADINGS,
							Result_of_math = raw_data$MathResult,
							Result_of_letter = raw_data$LetterResult,
							RT = raw_data$TestPhaseRT*1000
							)
		# remove study phase
		requirement <- is.na(Data$Result_of_letter)
		Data <- Data[requirement == FALSE, ]
		# add duration of math
		Data$Duration_of_math <- rep(na.omit(raw_data$ResponseTimeForExperiment)*1000, times = dim(Data)[1])
		# remove practice stage
		Data <- Data[1:length_of_practice*(-1), ]
		# recode variable
		Data <- recode_variable(Data)
		# export file
		export_file_name <- paste(Data$ID[1], "_", file_name, sep = "")
		export_file(Data, export_path, export_file_name)

		######################################################################################################################################################################
		
		# analysis
		result_data <- analysis(Data)
		# record result
		online_result[online_result$ID == Data$ID[1], -1] <- result_data
		}
	}
# export file
export_file_name <- result_file_name
export_file(online_result, ana_import_path, export_file_name)
cat("Files have been saved.\n\n\n\n\n\n", fill = TRUE)






# quite session
q(save = "no")