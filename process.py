import csv
import glob
from collections import defaultdict

files = glob.glob('*.txt')
pair = defaultdict(list)
header = ""
for file in files:
	header = "%s %s %s" % (header, file, "\t")
	if not bool(pair):
		with open(file) as csvfile:
			csvrows = csv.reader(csvfile, delimiter='\t')
			next(csvrows)
			for id, source, study in csvrows:
				pair[source].append(study)
			continue
			
	with open(file) as csvfile:
		csvrows = csv.reader(csvfile, delimiter='\t')
		next(csvrows)
		for id, source, study in csvrows:
			if source in pair:
				pair[source].append(study)

# string magic				
f = open("pair.csv","w+")
f.write(header + "\n")
for item in pair:
	for i in pair[item]:
		f.write(str(i) + "\t")
	f.write("\n")
f.close()
