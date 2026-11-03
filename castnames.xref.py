#!/usr/bin/env python3
import sys, re

#usage: tsv file exported from spreadsheets as single arg, stdin names to investigate
if len(sys.argv) != 2:
  raise Exception("need one arg, tsv from spreadsheet, to get name/film mappings")

filmtsvfn = sys.argv[1]

name2filmtitles = {}
print(f"get name/film mappings from {filmtsvfn}")
namecolnums = []
titlecolnum = None
maxcolneeded = 0
if True:
 filmtsvh = open(filmtsvfn)
 for ln in filmtsvh:
   ln = ln.strip()
   cols = ln.split("\t")
   if titlecolnum == None:
     for colnum, colname in enumerate(cols):
       #print(f"col {colname}")
       if re.search(r'(?i)(filed.*dir.*star|writer|director|stars|cast)',colname):
         print(f"namecol: {colname}")
         namecolnums.append(colnum)
         if colnum >= maxcolneeded:
           maxcolneeded = colnum
       elif re.search(r'(?i)(^title)',colname):
         print(f"titlecol: {colname}")
         titlecolnum = colnum
         if colnum >= maxcolneeded:
           maxcolneeded = colnum
     if titlecolnum == None: raise Exception("no title col found")
     if len(namecolnums) < 2: raise Exception("too few name cols")
   elif len(cols) >= maxcolneeded:
     title = cols[titlecolnum]
     title = re.sub(r'\(.*?\)',' ',title)
     title = re.sub(r'(?i)\s*,\s*the.*$','',title)
     title = re.sub(r'\*\S+',' ',title)
     title = " ".join(title.split())
     for colnum in namecolnums:
       for name in cols[colnum].split(","):
         if len(name) > 0:
           if name not in name2filmtitles:
             name2filmtitles[name] = []
           name2filmtitles[name].append(title)
for name in sorted(name2filmtitles):
  print(name+": "+",".join(name2filmtitles[name]))

