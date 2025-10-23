#!/usr/bin/env python3
import re, sys

objidpats = [
 r'.+',
 r'',
]

objidpatcounts = {}
for pat in objidpats: objidpatcounts[pat] = 0

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
          continue

# counts of
for patandcount in sorted(objidpatcounts.items(), key=lambda item: item[1]):
  print(str(patandcount[1])+"\t^"+patandcount[0]+"$")
