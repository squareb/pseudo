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
	# trim whitespaces around string
	string = string.strip()
	return string

"""
simple logger to write messages to a .txt file for later reference (i.e. warnings, errors and timestamps)
"""
def logger(string, console=False):
	log = open("logfile_processSpss.txt", "a+")
	log.write(string)
	log.write("\n")
	log.close()

	if console:
		print(string)

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
logger("Pairing file ready; peek: %s <-> %s" % (list(pairKey.keys())[0], pairKey[list(pairKey.keys())[0]]), console=True)

""" 
process spss files
"""
# determine spss files
spssFilesPath = sanitizeInput(input("Please provide the location of the spss files: "))
spssFiles = glob.glob(spssFilesPath + '/*.sav')
savRestrictionFile = sanitizeInput(input("Please provide the spss file used for restriction (leave this empty if you do not want to restrict): "))

# determine the id-variable from the spss file for pseudonimization
spssFilesIdVariable = b"PSEUDOIDEXT"

# read the spss file for restriction and restrict the dictionary
pairKeySubstitute = {}
if savRestrictionFile:
	with savReaderWriter.SavReader(savRestrictionFile, selectVars=[spssFilesIdVariable]) as reader:
		savRestrictionFileData = reader.all()
	# if the id identified from the file is in the dictionary, remove it via pop()
	for pseudoid in savRestrictionFileData:
		newkey = list(pairKey.keys())[list(pairKey.values()).index(pseudoid[0].decode('utf-8'))]
		pairKeySubstitute[newkey] = pairKey.pop(list(pairKey.keys())[list(pairKey.values()).index(pseudoid[0].decode('utf-8'))], None)
	pairKey = pairKeySubstitute

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
	# for each record from the spss file
	savFileDataNew = []
	for record in savFileData:
		try:
			# strip the pseudoid so that we only have an integer (also decode it; this is a feature of savReaderWriter)
			pseudoid = re.search(r'\d+',record[indexid].decode('utf-8')).group()
		# AttributeError occurs when record[index] is an empty string (can't do .group() on an empty string)
		except (AttributeError) as err:
			continue
		if pseudoid in pairKey.keys():		
			# replace the old pseudoid with the new one and encode it
			record[indexid] = pairKey[pseudoid].encode()
			savFileDataNew.append(record)
		
	originalRecordAmount = len(savFileData)
	if originalRecordAmount != len(savFileDataNew):
		logger("Warning: a total number of %s records are not paired and are removed from the new file: %s" % (originalRecordAmount - len(savFileDataNew), savFileName))

	# store the results in a new spss file
	savFileNameNew = "%s%s%s" % (spssFilesPath, '/generated/', os.path.basename(savFileName))
	try:
		with savReaderWriter.SavWriter(savFileNameNew, savFileHeader, savVarTypes, 
			valueLabels=metadata['valueLabels'], varLabels=metadata['varLabels'], 
			formats=metadata['formats'], measureLevels=metadata['measureLevels'], 
			columnWidths=metadata['columnWidths'], alignments=metadata['alignments'], ioUtf8=True) as writer:
			writer.writerows(savFileDataNew)
	except (ValueError, MemoryError) as err:
		logger("Error: %s" % (str(err)), console=True)
		if(type(err) is ValueError):
			logger("A ValueError has occured, please check if the (spss) files contain only the pseudoidentifiers from the depseudonimization files", console=True)
		if(type(err) is MemoryError):
			logger("A MemoryError has occured, the file you are trying to process is too big and there is not enough internal memory available. Please decrease the file size and try again", console=True)

	# update the progress bar
	progress += 1
	update_progress("Processing spss files", progress/(len(spssFiles) + 1))

logger("For warnings, please check the log in: %s" % (os.getcwd()), console=True)
logger("Stopped execution @ %s" % (datetime.datetime.now()))