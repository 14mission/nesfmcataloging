#!/usr/bin/env python3
import sys,os,re

intsvlist = []
av = sys.argv[1:]
ac = 0
while ac < len(av):
  if av[ac] == "-h": print("usage: "+sys.argv[0]+" -h(elp) inputfiles*tsv -o outputfile.tsv")
  elif av[ac][0] == "-": raise Exeption("unkflag: "+av[ac])
  else: intsvlist.append(av[ac])
  ac += 1

outcols = ["objid","title","shelvingcode","location"]

for intsv in intsvlist:
  if re.match(r'(?i).*(de\W*a[cs]*se[cs]+ion|4cit)',intsv):
    print(f"SKIP {intsv}")
    continue

  # output file
  outfn = intsv
  outfn = re.sub(r'\.\w+$','',outfn)
  outfn += ".4cit.tsv"
  print(f"write to {outfn}")
  outh = open(outfn,"w")
  print("\t".join(outcols)+"\tsource\tline",file=outh)

  # short name of file to put in output
  source = intsv
  source = re.sub(r'^.*- *','',source)
  source = re.sub(r'\.tsv$','',source)

  print(f"read {intsv}")
  inh = open(intsv)
  lnum = 0

  colmap = {}
  for field in outcols:
    colmap[field] = None

  for ln in inh:
    lnum += 1
    lncols = ln.split("\t")
    lncols[-1] = lncols[-1].strip()

    # header line?
    if colmap["objid"] == None:
      for colnum, colstr in enumerate(lncols):
        if re.match(r'Acc?ession Num',colstr): colmap["objid"] = colnum
        elif re.match(r'Title',colstr): colmap["title"] = colnum
        elif re.match(r'(Shelving|Bartel *-* *Thomsen Film Code)',colstr): colmap["shelvingcode"] = colnum
        elif re.match(r'Film Rack',colstr): colmap["location"] = colnum
        elif re.match(r'Series',colstr): colmap["series"] = colnum; print("series col")
      for field in sorted(colmap.keys()):
        if colmap[field] == None:
          raise Exception("no "+field+" col found in "+intsv+": hdrcols="+",".join(lncols))
        print(field + "=" + str(colmap[field]) + "=" + lncols[colmap[field]])
      continue

    # section divider line?
    if len([col for col in lncols if col != None and len(col.strip())>0]) <= 2:
      print("skip section header line: "+str(lnum)+": "+ln.strip())
      continue

    # regular line.  make sure all fields filled
    for colname in outcols:
      if lncols[colmap[colname]] == None or len(lncols[colmap[colname]].strip()) == 0:
        raise Exception("empty "+colname+" in "+intsv+":"+str(lnum)+": "+ln.strip())
    # if series col, and filled, prefix to title
    if "series" in colmap and len(lncols[colmap["series"]].strip()):
      lncols[colmap["title"]] = lncols[colmap["series"]].strip() + ": " + lncols[colmap["title"]]

    # then print
    print("\t".join(lncols[colmap[colname]] for colname in outcols)+"\t"+source+"\t"+str(lnum), file=outh)
