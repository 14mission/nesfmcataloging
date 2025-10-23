#!/usr/bin/env python3
import re, sys

# patterns to look for
# arrange in order to check them
objidpats = [
 r'\d\d\d\d\.\d+\.\d+',
 r'\d\d\d\d\.\d+\.\d+[\s-]?[A-Za-z]',
 r'MG\d+',
 r'MG\d+-\d+',
 r'MG\d+(-\d+)?-?[A-Za-z]+(-\d+|-[A-Za-z]+)*',
 r'A-\d+',
 r'(?i:)\W*unknown\W*',
 r'#\d+\.\d+',
 r'20xx.xx.xx',
 r'.+',
 r'',
]

# count number of times each pattern matched
# keep first 10 examples
objidpatcounts = {}
objidpatexamples = {}
for pat in objidpats:
  objidpatcounts[pat] = 0
  objidpatexamples[pat] = []

for fn in sys.argv[1:]:

  # ignore certain files: "deaccessioned", "video", and files written by this program
  if re.match(r'(?i).*(de\W*a[cs]*se[cs]+ion|video|4cit)',fn):
    print(f"SKIP {fn}")
    continue

  print("read "+fn)

  inh = open(fn)
  objcol = None

  for ln in inh:

    cols = ln.split("\t")
    cols[-1] = cols[-1].strip()

    # header line
    if objcol == None:
      for colnum, colstr in enumerate(cols):
        if re.match(r'(?i)access.*num',colstr):
          print(f"use col {colnum} \"{colstr}\"")
          objcol = colnum
      if objcol == None:
        raise Exception(f"no accession number col found in {fn}")

    # data line
    else:
      objid = cols[objcol].strip()
      # find pattern that matches objecid
      for pat in objidpats:
        if re.match(r'^'+pat+'$',objid):
          objidpatcounts[pat] += 1
          objidpatexamples[pat].append(objid)
          break

# counts of
print("cnt\tpat\texamples")
for pat, count in sorted(objidpatcounts.items(), reverse=True, key=lambda item: item[1]):
  print(str(count)+"\t^"+pat+"$"+"\t" + ", ".join(example if len(example) else "EMPTY" for example in objidpatexamples[pat][:10]))
print("misc")
for oddball in objidpatexamples[r'.+']:
  print(oddball)
