#!/usr/bin/env python3

mgninfo = {}
mgnfn = "emgee_numerical.tsv"
print(f"read {mgnfn}")
mgnf = open("emgee_numerical.tsv")
for ln in mgnf:
  ln = ln.strip()
  if len(ln) == 0 or ln[0] == "#":
    continue
  cols = ln.split("\t")
  if len(cols) < 2:
    print("ignore: "+ln)
  mgninfo[cols[0]] = cols[1]
print("read "+str(len(mgninfo))+" entries")
