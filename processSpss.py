"""
purpose:	repseudonimize spss files replacing the original identifier with a new identifier using a common (source) identifier 
input:		.sav file, .txt depseudonimize file (for the original identifier), .txt depseudonimize file (for the new identifier)
output:		.sav file
"""
#TODO: error handling

import os, sys, glob, time, csv, re, contextlib
from collections import defaultdict

# doc: https://pythonhosted.org/savReaderWriter/generated_api_documentation.html
import savReaderWriter

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
#TODO: try to make more elegant without increasing the risk of human and/or sequencing errors

# determine depseudonimization files
pseudoOriginalFile = input("Please provide the full path, including file name, of the depseudonimize file with the original identifiers: ")
pseudoNewFile = input("Please provide the full path, including file name, of the depseudonimize file with the new identifiers: ")

# create a dictionary containing the source identifiers (key) with the original identifiers
pseudoOriginalData = defaultdict(str)
with open(pseudoOriginalFile) as csvfile:
	csvrows = csv.reader(csvfile, delimiter='\t')
	next(csvrows)
	for id, source, study in csvrows:
		pseudoOriginalData[source] = study
csvfile.close()

# create a dictionary pairing the original identifier (key) with the new identifier based on the common source identifier
pairKey = {}
with open(pseudoNewFile) as csvfile:
	csvrows = csv.reader(csvfile, delimiter='\t')
	next(csvrows)
	for id, source, study in csvrows:
		if(source in pseudoOriginalData.keys()):
			pairKey[pseudoOriginalData[source]] = study
csvfile.close()

# for validation purposes, return the first key/value pair of the dictionary (note: dictionaries do not guarantee order)
print("Pairing file ready; peek: " + list(pairKey.keys())[0] + " <-> " + pairKey[list(pairKey.keys())[0]])

""" 
process spss files
"""
# determine spss files
spssFilesPath = input("Please provide the location of the spss files: ")
spssFiles = glob.glob(spssFilesPath + '/*.sav')

# create a folder to store the new files
dirName = "/generated"
if not os.path.exists(spssFilesPath + dirName):
	os.mkdir(spssFilesPath + dirName)

# update the progress bar pre-liminary to display it. Next updates will be after a file is processed, until all files are done
progress += 1
update_progress("Processsing spss files: ", progress/(len(spssFiles) + 1))

for file in spssFiles:
	savFileHeader, savFileData = [[],[]]
	savFileName = file

	# suppress output to console, as SavReader contains an unfortunate print() statement
	with contextlib.redirect_stdout(None):
	# read the spss file
		with savReaderWriter.SavReader(savFileName, returnHeader=True) as reader:
			savFileData = reader.all()
			savFileHeader = savFileData.pop(0)

	savVarTypes, savVarLabels, savValueLabels = ["", "", ""]
	with savReaderWriter.SavHeaderReader(savFileName) as header:
		metadata = header.dataDictionary()
		savVarTypes = metadata['varTypes']
		savVarFormats = metadata['formats']
		savVarLabels = metadata['varLabels']
		savValueLabels = metadata['valueLabels']

	# for each record from the spss file
	for record in savFileData:
		# strip the pseudoid so that we only have an integer (also decode it; this is a feature of savReaderWriter)
		pseudoid = re.search(r'\d+',record[0].decode('utf-8')).group()
		if pseudoid in pairKey.keys():
			# replace record[0] if a match is found and encode it
			record[0] = pairKey[pseudoid].encode() 

	# store the results in a new spss file
	#TODO: check refSavFileName parameter for copying metadata
	savFileName = "%s%s%s" % (spssFilesPath, '/generated/p', os.path.basename(savFileName))
	with savReaderWriter.SavWriter(savFileName, savFileHeader, savVarTypes, 
		valueLabels=savValueLabels, varLabels=savVarLabels, formats=savVarFormats) as writer:
		writer.writerows(savFileData)

	# update the progress bar
	progress += 1
	update_progress("Processsing spss files: ", progress/(len(spssFiles) + 1))

