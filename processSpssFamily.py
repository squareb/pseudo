"""
purpose:	repseudonimize spss files replacing the original identifier with a new identifier using a common (source) identifier 
input:		.sav file, .txt depseudonimize file (for the original identifier), .txt depseudonimize file (for the new identifier)
output:		.sav file
"""

import os, sys, glob, datetime, csv, re, contextlib, hashlib, random
from collections import defaultdict

# doc: https://pythonhosted.org/savReaderWriter/generated_api_documentation.html
import savReaderWriter
import pandas as pd

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
scrambler
"""
def scrambler(pseudoid, random_seed):
	# use a hash function to scramble the number portion of the 'S' value
	salted_value = f"{pseudoid}{random_seed}"  # append seed to value to ensure randomness
	hash_object = hashlib.sha256(salted_value.encode())
	# convert the hash to an integer and take the last 7 digits
	scrambled_number = str(int(hash_object.hexdigest(), 16))[-12:]
	return scrambled_number


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
progress = 0
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
	csvrows = csv.reader(csvfile, delimiter=',')
	next(csvrows)
	for source, study in csvrows:
		pseudoOriginalData[source] = study
		pseudoOriginalCount += 1
csvfile.close()

# create a dictionary pairing the original identifier (key) with the new identifier based on the common source identifier
pairKey = {}
pseudoNewCount = 0
with open(pseudoNewFile) as csvfile:
	csvrows = csv.reader(csvfile, delimiter=',')
	next(csvrows)
	for source, study in csvrows:
		if(source in pseudoOriginalData.keys()):
			pairKey[pseudoOriginalData[source]] = study
		pseudoNewCount += 1
csvfile.close()

# log the total number of identifiers between the files and a possible warning if these are not equal
logger("File containing original pseudoidentifiers: %s counting %s records" % (pseudoOriginalFile, pseudoOriginalCount))
logger("File containing new pseudoidentifiers: %s counting %s records" % (pseudoNewFile, pseudoNewCount))
if pseudoOriginalCount != pseudoNewCount:
	logger("Warning: depseudonimize files do not contain an equal amount of identifiers!", console=True)

# for validation purposes, return the first key/value pair of the dictionary (note: dictionaries do not guarantee order)
logger("Pairing file ready; peek: " + list(pairKey.keys())[0] + " <-> " + pairKey[list(pairKey.keys())[0]], console=True)

""" 
process spss files
"""
# determine spss files
spssFilesPath = sanitizeInput(input("Please provide the location of the spss files: "))
spssFilesPath = "./spss" if spssFilesPath == "" else spssFilesPath
spssFiles = glob.glob(spssFilesPath + '/*.sav')

# determine the id-variable(s) from the spss file for pseudonimization
spssFilesIdVariableList = sanitizeInput(input("Please provide one or more variables that need repseudonimization (use , as seperator): "))
spssFilesIdVariableList = spssFilesIdVariableList.split(",")
spssFilesIdVariableList = [variable.encode() for variable in spssFilesIdVariableList]

# generate a seed to create random S-identifiers (if applicable). Existing seeds can also be provided.
random_seed = sanitizeInput(input("Input seed to reuse existing S-identifiers (leave blank if you want to generate new S-identifiers): "))
if not random_seed:
	random_seed = random.randint(0, int(1e6))

# create a folder to store the new files
dirName = "\\2.For researcher"
parentDir = os.path.normpath(os.path.join(spssFilesPath, '..\\..'))
if not os.path.exists(parentDir + dirName):
	os.mkdir(parentDir + dirName)

# update the progress bar pre-liminary to display it. Next updates will be after a file is processed, until all files are done
progress += 1
update_progress("Processing spss files", progress/(len(spssFiles) + 1))

for file in spssFiles:
	savFileHeader, savFileData = [[],[]]
	savFileName = file

	# read the spss file
	with savReaderWriter.SavReader(savFileName, returnHeader=True, rawMode=True) as reader:
		savFileData = reader.all()
		savFileHeader = savFileData.pop(0)

	# retrieve meta-data 
	savVarTypes = {}
	with savReaderWriter.SavHeaderReader(savFileName) as header:
		metadata = header.dataDictionary()
		savVarTypes = metadata['varTypes']
	
	savFileDataNew = []
	
	# for each record from the spss file
	for record in savFileData:
		recordExists = False
		for spssFilesIdVariable in spssFilesIdVariableList:
			# get the index location of index variable based on the header (variable name)
			indexid = savFileHeader.index(spssFilesIdVariable)
			pseudoid = record[indexid]
			
			# if pseudoid is an original (SPSS) string, it is typed as 'bytes'. This requires unicode-decoding.
			if isinstance(pseudoid, bytes):
				# strip the pseudoid so that we only have an integer (also decode it; this is a feature of savReaderWriter)
				pseudoid = pseudoid.decode('utf-8').strip()

				# if pseudoid is in the existing key dictionary, replace it with the keypair
				if pseudoid in pairKey:
					# replace the old pseudoid with the new one and encode it
					record[indexid] = pairKey[pseudoid].encode('utf-8')
					# track this record, as any replaced pseuodid with a valid value needs to be present in the new file
					recordExists = True
				
				# some values may be formatted as S[0-9], this requires seperate scrambling because there's no corresponding key
				elif re.match(r'^S\d{7}$', pseudoid):
					scrambled_number = scrambler(pseudoid, random_seed)
					pseudoid = 'S' + scrambled_number
					record[indexid] = pseudoid.encode('utf-8')
					# track this record, as any record that has an S-number, needs to be present in the new file
					recordExists = True
				
				# some values are an explicit 0, leave these as they are.
				elif pseudoid == "0":
					record[indexid] = pseudoid.encode('utf-8')
					
				# if the pseudoid is not in the existing key dictionary, scramble it and replace it
				else:
					scrambled_number = scrambler(pseudoid, random_seed)
					pseudoid = 'P' + scrambled_number
					record[indexid] = pseudoid.encode('utf-8')
	
			# if variables are a float, scramble and replace them.
			elif isinstance(pseudoid, float):
				pseudoid = str(int(pseudoid))
				scrambled_number = scrambler(pseudoid, random_seed)
				record[indexid] = int(scrambled_number)

			# for all other values, give an error, as these are not expected
			else:
				logger("\nERROR: Unknown variable type (no String or Float) detected", console=True)
				sys.exit(1)
			
		# if a pseudoid has been changed, append the record. Otherwise the identifier is not available in the new pseudo-file
		if recordExists: 
			savFileDataNew.append(record)
		
	originalRecordAmount = len(savFileData)
	if originalRecordAmount != len(savFileDataNew):
		logger("\nWarning: a total number of %s records are not paired and are removed from the new file: %s" % (originalRecordAmount - len(savFileDataNew), savFileName), console=True)

	# store the results in a new spss file
	savFileNameNew = "%s%s%s%s" % (parentDir, dirName, '/', os.path.basename(savFileName))
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

	df = pd.read_spss(savFileNameNew)
	csvFileName = "%s%s" % (savFileNameNew.rstrip(savFileNameNew[-4:]), '.csv')
	df.to_csv(csvFileName, index=False)
	
	# update the progress bar
	progress += 1
	update_progress("Processing spss files", progress/(len(spssFiles) + 1))

# export seed so that it can be reused for the same study.
seedFileName = "%s%s" % (parentDir, '\\seed_number.txt')
f = open(seedFileName, 'w')
f.write("Copy the seed number generated in the first generated file here.\nSeed number=" + str(random_seed))
f.close()
logger("Stopped execution @ %s" % (datetime.datetime.now()))