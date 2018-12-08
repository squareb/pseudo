"""
purpose:	repseudonimize spss files replacing the original identifier with a new identifier using a common (source) identifier 
input:		.sav file, .txt depseudonimize file (for the original identifier), .txt depseudonimize file (for the new identifier)
output:		.sav file
"""

import csv
import glob
import re
from collections import defaultdict

import savReaderWriter

"""spss pairing example"""
# determine files and define variables
savFileHeader = []
savFileData = []
savFileName = "./spss/Example.sav"

#TODO: make it so that we can process n spss files
# read the spss file
with savReaderWriter.SavReader(savFileName, returnHeader=True) as reader:
	savFileHeader = next(reader)
	for record in reader:
		savFileData.append(record)
reader.close()

#TODO: check on input of depseudonomization files, there need to be two (at the moment)
# determine depseudonimization files and define variables
files = glob.glob('./spss/*.txt')
rePseudoData = defaultdict(list)

# for each file
for file in files:
	# open single file
	with open(file) as csvfile:
		csvrows = csv.reader(csvfile, delimiter='\t')
		next(csvrows)
		# append each row to the pairing file
		for id, source, study in csvrows:
			rePseudoData[source].append(study)
	
	csvfile.close()

#TODO: there can only be two depseudonimization files (at the moment)
# remodel the dictionary having the original id as the key and the new id as the value
pairKey = {}
for k, v in rePseudoData.items():
	pairKey[v[0]] = v[1]

# for each record from the spss file
for record in savFileData:
	# strip the pseudoid so that we only have an integer (also decode it; this is a feature of savReaderWriter)
	pseudoid = re.search(r'\d+',record[0].decode('utf-8')).group()
	if pseudoid in pairKey.keys():
		# replace record[0] if a match is found and encode it
		record[0] = pairKey[pseudoid].encode() 

# store the results in a new spss file
savFileName = "./spss/Example_NEW.sav"
varTypes = {b'ID': 20, b'Age': 0, b'Sex': 0, b'City': 20} #TODO: 1) why is 20 multiplied by 3 as a string type? 2) make this dynamic
with savReaderWriter.SavWriter(savFileName, savFileHeader, varTypes) as writer:
    for record in savFileData:
        writer.writerow(record)