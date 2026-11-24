#!/usr/bin/env python3
import sys, locale, unicodedata, re
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
curbatch = []
for curln in sys.stdin:
  curln = curln.strip()
  if len(curln) == 0:
    pass
  elif re.match(r'^#.* from ',curln):
    print("section: "+curln,file=sys.stderr)
    print("prev: "+str(len(curbatch))+" lines",file=sys.stderr)
    curbatch.sort(key=locale.strxfrm)
    for batchln in curbatch:
      print(batchln)
    curbatch = []
    print(curln)
  else:
    curbatch.append(curln)
print("eof",file=sys.stderr)
print("prev: "+str(len(curbatch))+" lines",file=sys.stderr)
curbatch.sort(key=locale.strxfrm)
for batchln in curbatch:
  print(batchln)
