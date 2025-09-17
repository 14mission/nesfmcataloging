#!/usr/bin/env python3
import sys,os,re

intsvlist = []
outtsvfn = None
av = sys.argv[1:]
ac = 0
while ac < len(av):
  if av[ac] == "-h": print("usage: "+sys.argv[0]+" -h(elp) inputfiles*tsv -o outputfile.tsv")
  elif av[ac] == "-o" and ac+1 < len(av) and av[ac+1][0] != "-": ac+1; outtsvfn = av[ac]
  elif av[ac][0] == "-": raise Exeption("unkflag: "+av[ac])
  else: intsvlist.append(av[ac])
  ac += 1

if outtsvfn == None:
  print("write to stdout")
  outh = sys.stdout
else:
  print(f"write to {outtsvfn}")
  outh = open(outtsvfn,"w")

for intsv in intsvlist:
  if re.match(r'(?i).*de\W*a[cs]*se[cs]+ion',intsv):
    print(f"SKIP {intsv}")
    continue

  print(f"read {intsv}")
  inh = open(intsv)
  lnum = 0

  colmap = { "objid":None, "title":None, "shelvingcode":None, "location":None }

  for ln in inh:
    lncols = ln.split("\t")
    lncols[-1] = lncols[-1].strip()
    if colmap["objid"] == None:
      for colnum, colstr in enumerate(lncols):
        if re.match(r'Acc?ession Num',colstr): colmap["objid"] = colnum
        elif re.match(r'Title',colstr): colmap["title"] = colnum
        elif re.match(r'(Shelving|Bartel *-* *Thomsen Film Code)',colstr): colmap["shelvingcode"] = colnum
        elif re.match(r'Film Rack',colstr): colmap["location"] = colnum
      for field in sorted(colmap.keys()):
        if colmap[field] == None:
          raise Exception("no "+field+" col found in "+intsv+": hdrcols="+",".join(lncols))
        print(field + "=" + str(colmap[field]) + "=" + lncols[colmap[field]])

    lnum += 1
