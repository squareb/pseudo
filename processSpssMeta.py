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
process spss files
"""
# determine spss files
spssFilesPath = sanitizeInput(input("Please provide the location of the spss files: "))
spssFilesPath = "./spss" if spssFilesPath == "" else spssFilesPath
spssFiles = glob.glob(spssFilesPath + '/*.sav')

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

	# retrieve meta-data 
	metadata = {}
	with savReaderWriter.SavHeaderReader(savFileName) as header:
		metadata = header.dataDictionary()

	savMetaFileNameNew = "%s%s%s" % (spssFilesPath, '/generated/', os.path.basename(savFileName + ".txt"))
	metadataFile = open(savMetaFileNameNew, "w+")
	for item in metadata:
		if item in ["varLabels", "valueLabels", "varNames"]:
			metadataFile.write(item)
			metadataFile.write("\n")
			metadataFile.write(str(metadata[item]).replace('b\'', '\''))
			metadataFile.write("\n\n")
	metadataFile.close()

	# update the progress bar
	progress += 1
	update_progress("Processing spss files", progress/(len(spssFiles) + 1))
logger("Stopped execution @ %s" % (datetime.datetime.now()))