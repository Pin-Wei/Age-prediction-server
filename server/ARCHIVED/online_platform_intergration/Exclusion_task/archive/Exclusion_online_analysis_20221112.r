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
		for (j in 1:number_of_zeros)
			{
			zeros <- paste(zeros, "0", sep = "")
			}
		subject_number[i] <- paste("PAV", "-", zeros, as.character(subject_number[i]), sep = "")
		}
	return(subject_number)
	}
# recode string variable
recode_string_variable <- function(Data, keyword, i)
	{
	index <- which(colnames(Data) == keyword)
	split_string <- strsplit(Data[, index][i], "/")
	split_string <- strsplit(split_string[[1]][length(split_string[[1]])], "[.]")
	split_string <- split_string[[1]][1]
	return(split_string)
	}
# recode variable
recode_variable <- function(Data)
	{
	for (i in 1:dim(Data)[1])
		{
		# recode "" in keypress as NA
		requirement <- Data$Keypress[i] == ""
		if (requirement == TRUE)
			{
			Data$Keypress[i] <- NA
			Data$Type_of_response[i] <- NA
			} else
			{
			# recode accuracy
			if (Data$Keypress[i] == "s")
				{
				if (Data$Type_of_stimulus[i] == 1)
					{
					Data$Accuracy[i] <- 1 
					} else
					{
					Data$Accuracy[i] <- 0
					}
				} else if (Data$Keypress[i] == "k")
				{
				if (Data$Type_of_stimulus[i] != 1)
					{
					Data$Accuracy[i] <- 1
					} else
					{
					Data$Accuracy[i] <- 0
					}
				}
			}
		# recode Picture
		Data$Picture[i] <- recode_string_variable(Data, "Picture", i)
		# recode Type_of_cue
		Data$Type_of_cue[i] <- recode_string_variable(Data, "Type_of_cue", i)
		# recode type of response
		Data$Type_of_response[i] <- 100*Data$Number_of_cue[i] + 10*Data$Type_of_stimulus[i] + Data$Accuracy[i]
		}
	return(Data)
	}
# analysis
analysis <- function(Data, levels_of_number_of_cue)
	{
	result_data <- NULL
	for (j in 1:length(levels_of_number_of_cue))
		{
		for (k in 1:length(type_of_response_factor))
			{
			factor <- levels_of_number_of_cue[j]*100 +  type_of_response_factor[k]
			requirement_1 <- Data$Type_of_response == factor
			if (k <= 3)
				{
				# ratio
				requirement_2 <- Data$Number_of_cue == levels_of_number_of_cue[j] & Data$Type_of_stimulus == k
				input_data_1 <- Data$Accuracy[requirement_1 == TRUE]
				input_data_2 <- Data$Picture[requirement_2 == TRUE]
				result <- length(na.omit(input_data_1))/length(na.omit(input_data_2))
				} else
				{
				# RT
				input_data <- Data$RT[requirement_1 == TRUE]
				result <- mean(na.omit(input_data))
				}
			result <- round(result, digits = 3)
			result_data <- c(result_data, result)
			}
		}
	return(result_data)
	}
# export file
export_file <- function(Data, export_path, export_file_name)
	{
	export_file <- paste(export_path, "/", export_file_name, sep = "")
	write.csv(Data, export_file, row.names = FALSE)
	cat(export_file, fill = TRUE)
	}
# type of stimulus*10 + accuracy
type_of_response_factor <- c(11, 20, 30, 11, 10, 20, 21, 30, 31)
ana_import_path <- "../../../beh/online_experiment/ana"
raw_data_import_path <- "../../../beh/online_experiment/raw_data"
export_path <- "../../../beh/online_experiment"
file_name <- "EX_online.csv"
result_file_name <- "Exclusion_online_result.csv"
##### parameters #####



# specify subject number
subject_number <- c(16, 17)



# import online esult data
online_result <- read.csv(paste(ana_import_path, "/", result_file_name, sep = ""))
# file list in raw data folder
file_list <- list.files(raw_data_import_path)
# create ID
subject_number <- create_ID(subject_number)
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
							Picture = raw_data$picname_t,
							Type_of_cue = raw_data$type_of_cue_t,
							Number_of_cue = raw_data$number_of_cue_t,
							Type_of_stimulus = raw_data$stimuli_t,
							Keypress = raw_data$key_resp.keys,
							Accuracy = NA,
							RT = raw_data$key_resp.r*1000,
							Type_of_response = NA
							)
		# remove study phase
		requirement <- is.na(Data$Type_of_stimulus)
		Data <- Data[requirement == FALSE, ]
		# remove practice stage
		Data <- Data[1:3*(-1), ]
		# recode variable
		Data <- recode_variable(Data)
		# export file
		export_file_name <- paste(Data$ID[1], "_", file_name, sep = "")
		export_file(Data, export_path, export_file_name)

		######################################################################################################################################################################
		
		# analysis
		levels_of_number_of_cue <- sort(unique(Data$Number_of_cue))
		result_data <- analysis(Data, levels_of_number_of_cue)
		# record result
		result_data <- c(Data$ID[1], as.character(result_data))
		online_result <- rbind(online_result, result_data)
		}
	}
# sort ID in online result data
online_result <- online_result[order(online_result$ID), ]
# export file
export_file_name <- result_file_name
export_file(online_result, ana_import_path, export_file_name)
cat("Files have been saved.\n\n\n\n\n\n", fill = TRUE)






# quite session
q(save = "no")