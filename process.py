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
		# for each row
		for id, source, study in csvrows:
			# if source pseudo is in the dict, and pair is not empty
			if source in pair and bool(pair):
				pair[source].append(study)
			else:
				pair[source].append(study)
	
	csvfile.close()

# compose the new file				
f = open("pair.csv","w+")
f.write(header + "\n")
for item in pair:
	for i in pair[item]:
		f.write(str(i) + "\t")
	f.write("\n")
f.close()
