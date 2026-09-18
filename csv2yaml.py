#!/usr/bin/env python3
import sys,csv,re

for csvfn in sys.argv[1:]:
  colnames = None
  rawreader = open(csvfn)
  csvreader = csv.reader(rawreader)
  ymlfn = re.sub(r'\.csv$','',csvfn) + ".yml"
  ymlwriter = open(ymlfn,"w")
  print(f"convert {csvfn} -> {ymlfn}")
  for row in csvreader:
    if colnames == None:
      colnames = row
    else:
      for colnum, colval in enumerate(row):
        if colnum == 0:
          print(row[0]+":", file=ymlwriter)
        elif colval != None and len(colval.strip()) > 0:
          print(" "+colnames[colnum]+": "+colval.strip(), file=ymlwriter)
