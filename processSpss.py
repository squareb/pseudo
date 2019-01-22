"""
purpose:	repseudonimize spss files replacing the original identifier with a new identifier using a common (source) identifier 
input:		.sav file, .txt depseudonimize file (for the original identifier), .txt depseudonimize file (for the new identifier)
output:		.sav file
"""

import os, sys, glob, datetime, csv, re, contextlib
from collections import defaultdict

# doc: https://pythonhosted.org/savReaderWriter/generated_api_documentation.html
import savReaderWriter

"""
method to do various input sanitizations on user input.
"""
def sanitizeInput(string):
	# remove additional quotes
	string = string.replace("\"", "")
	return string

"""
simple logger to write messages to a .txt file for later reference (i.e. warnings, errors and timestamps)
"""
def logger(string):
	log = open("logfile_processSpss.txt", "a+")
	log.write(string)
	log.write("\n")
	log.close()

logger("\nRunning execution @ %s" % (datetime.datetime.now()))

"""
progress bar
"""
progress = 0;
def update_progress(job_title, progress):
	size = 20
	block = int(round(size*progress))
	msg = "\r{0}: [{1}] {2}%".format(job_title, "#"*block + "-"*(size-block), round(progress*100, 2))
	if progress >= 1: msg += " DONE\r\n"
	sys.stdout.write(msg)
	sys.stdout.flush()

"""
make a pairing key dictionary
""" 
# determine depseudonimization files
pseudoOriginalFile = sanitizeInput(input("Please provide the full path, including file name, of the depseudonimize file with the original identifiers: "))
pseudoNewFile = sanitizeInput(input("Please provide the full path, including file name, of the depseudonimize file with the new identifiers: "))

# create a dictionary containing the source identifiers (key) with the original identifiers
pseudoOriginalData = defaultdict(str)
# keep count of the number of pseudo's so we can later log and compare if there is a difference in total number of id's between the files
pseudoOriginalCount = 0
with open(pseudoOriginalFile) as csvfile:
	csvrows = csv.reader(csvfile, delimiter='\t')
	next(csvrows)
	for id, source, study in csvrows:
		pseudoOriginalData[source] = study
		pseudoOriginalCount += 1
csvfile.close()

# create a dictionary pairing the original identifier (key) with the new identifier based on the common source identifier
pairKey = {}
pseudoNewCount = 0
with open(pseudoNewFile) as csvfile:
	csvrows = csv.reader(csvfile, delimiter='\t')
	next(csvrows)
	for id, source, study in csvrows:
		if(source in pseudoOriginalData.keys()):
			pairKey[pseudoOriginalData[source]] = study
		pseudoNewCount += 1
csvfile.close()

# log the total number of identifiers between the files and a possible warning if these are not equal
logger("File containing original pseudoidentifiers: %s counting %s records" % (pseudoOriginalFile, pseudoOriginalCount))
logger("File containing new pseudoidentifiers: %s counting %s records" % (pseudoNewFile, pseudoNewCount))
if pseudoOriginalCount != pseudoNewCount:
	logger("Warning: depseudonimize files do not contain an equal amount of identifiers!")

# for validation purposes, return the first key/value pair of the dictionary (note: dictionaries do not guarantee order)
print("Pairing file ready; peek: " + list(pairKey.keys())[0] + " <-> " + pairKey[list(pairKey.keys())[0]])

""" 
process spss files
"""
# determine spss files
spssFilesPath = sanitizeInput(input("Please provide the location of the spss files: "))
spssFilesPath = "./spss" if spssFilesPath == "" else spssFilesPath
spssFiles = glob.glob(spssFilesPath + '/*.sav')

# determine the id-variable from the spss file for pseudonimization
spssFilesIdVariable = b"PSEUDOIDEXT"

# create a folder to store the new files
dirName = "/generated"
if not os.path.exists(spssFilesPath + dirName):
	os.mkdir(spssFilesPath + dirName)

# update the progress bar pre-liminary to display it. Next updates will be after a file is processed, until all files are done
progress += 1
update_progress("Processing spss files", progress/(len(spssFiles) + 1))

for file in spssFiles:
	savFileHeader, savFileData = [[],[]]
	savFileName = file

	# read the spss file
	with savReaderWriter.SavReader(savFileName, returnHeader=True) as reader:
		savFileData = reader.all()
		savFileHeader = savFileData.pop(0)

	# retrieve meta-data 
	savVarTypes = {}
	with savReaderWriter.SavHeaderReader(savFileName) as header:
		metadata = header.dataDictionary()
		savVarTypes = metadata['varTypes']

	# get the index location of index variable based on the header (variable name)
	indexid = savFileHeader.index(spssFilesIdVariable)
	# variables for keeping track of unmatched pseudoid's
	unmatchedPseudoid = []
	unmatchedWarningFlag = False
	# for each record from the spss file
	for record in savFileData:
		# strip the pseudoid so that we only have an integer (also decode it; this is a feature of savReaderWriter)
		#TODO: encoding sometimes leads to warnings when actually opening the file in spss
		pseudoid = re.search(r'\d+',record[indexid].decode('utf-8')).group()
		# check if the pseudoid is in the list of original identifiers
		if pseudoid in pairKey.keys():
			# replace the old pseudoid with the new one if a match is found and encode it
			record[indexid] = pairKey[pseudoid].encode() 
		# if the original pseudoid is not found, it will be registered in an array with unmatched pseudoid's (for future deletion)
		elif pseudoid not in unmatchedPseudoid:
			unmatchedPseudoid.append(pseudoid)
		
	# only keep the pseudoid's that are matched
	#TODO: does this improve performance over f.e. rewriting an unmatched pseudoid to a blank string ("")	
	savFileData = [record for record in savFileData if re.search(r'\d+',record[indexid].decode('utf-8')).group() not in unmatchedPseudoid]
	
	# log if pseudoid's have been unmatched and have been removed
	if(unmatchedWarningFlag):
		logger("Warning: one or several pseudoid's could not be matched in the following file: %s" % (savFileName))

	# store the results in a new spss file
	#TODO: check refSavFileName parameter for copying metadata
	savFileNameNew = "%s%s%s" % (spssFilesPath, '/generated/', os.path.basename(savFileName))
	with savReaderWriter.SavWriter(savFileNameNew, savFileHeader, savVarTypes, 
		valueLabels=metadata['valueLabels'], varLabels=metadata['varLabels'], 
		formats=metadata['formats'], measureLevels=metadata['measureLevels'], 
		columnWidths=metadata['columnWidths'], alignments=metadata['alignments']) as writer:
		writer.writerows(savFileData)

	# update the progress bar
	progress += 1
	update_progress("Processing spss files", progress/(len(spssFiles) + 1))