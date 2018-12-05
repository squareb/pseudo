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

	# open file
	with open(file) as csvfile:
		csvrows = csv.reader(csvfile, delimiter='\t')
		next(csvrows)
		# for each row, expect the header
		for id, source, study in csvrows:
			pair[source].append(study)
	
	csvfile.close()

# only store identifiers that are paired
pair = [pair[item] for item in pair if len(pair[item]) > 1]

# compose the new file				
f = open("pair.csv","w+")
f.write(header + "\n")
for item in pair:
	for i in item:
		f.write(str(i) + "\t")
	f.write("\n")
f.close()