import csv
import glob
from collections import defaultdict

# determine files and define variables
files = glob.glob('*.txt')
pair = defaultdict(list)
header = ""

# for each file
for file in files:

	# edit header
	header = file if header == "" else "%s %s %s" % (header, file, "\t") 

	# open single file
	with open(file) as csvfile:
		csvrows = csv.reader(csvfile, delimiter='\t')
		next(csvrows)
		# for each row, expect the header, append it to the pairing file
		for id, source, study in csvrows:
			pair[source].append(study)
	
	csvfile.close()

# keep pseudoidentifiers that have been paired more than once
pair = {source: studyList for source, studyList in pair.items() if len(studyList) > 1}

# compose the pairing file, tab-seperated and without the source key				
f = open("pair.csv","w+")
f.write(header + "\n")
for source in pair:
	for study in pair[source]:
		f.write(str(study) + "\t")
	f.write("\n")
f.close()