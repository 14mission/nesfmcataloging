#!/usr/bin/env python3
import re, glob

def normalizeid(idstr):
  idstr = re.sub(r'\W+','',idstr)
  idstr = idstr.upper()
  idstr = re.sub(r'(?i)^mg','',idstr)
  idstr = "MG"+idstr
  return idstr

print("READ EMGEE NUMERICAL")
mgninfo = {}
mgnfn = "emgee_numerical.tsv"
print(f"read {mgnfn}")
mgnf = open("emgee_numerical.tsv")
for ln in mgnf:
  ln = ln.rstrip()
  if len(ln) == 0 or ln[0] == "#":
    continue
  cols = ln.split("\t")
  if len(cols) < 2:
    print("ignore: "+ln)
  rawid = cols[0]
  text = "("+rawid+") "+cols[1]
  normedid = normalizeid(rawid)
  if normedid in mgninfo:
    print("normed id collision for: "+normedid+" "+mgninfo[normedid]+" _VS_ "+text)
    mgninfo[normedid] += " _AND_ "+text
  else:
    mgninfo[normedid] = text
print("found "+str(len(mgninfo))+" entries")
print("")

print("READ GSHTs")
gshtinfo = {}
for gshtfn in glob.glob("nesfm.archive.*tsv"):
  if re.search('(?i)(4cit|videos)', gshtfn): continue
  print(f"read {gshtfn}")
  gshtf = open(gshtfn)
  titlecolnum = None
  idcolnum = None
  numignored = 0
  for ln in gshtf:
    ln = ln.rstrip()
    cols = ln.split("\t")
    # header?
    if titlecolnum == None:
      for colnum, colstr in enumerate(cols):
        if "accession number" in colstr.lower(): idcolnum = colnum
        elif "title" in colstr.lower(): titlecolnum = colnum
      if idcolnum == None: raise Exception("no accession col")
      if titlecolnum == None: raise Exception("no title col")
      print("cols: "+cols[idcolnum]+", "+cols[titlecolnum])
    # regular row
    else:
      if len(cols) <= idcolnum or len(cols) <= titlecolnum:
        numignored += 1
        if numignored <= 3:
          print("ignore line: "+ln)
        elif numignored == 4:
          print("...")
        continue
      rawid = cols[idcolnum]
      #print("RAWID: "+rawid)
      if not re.match(r'^MG', rawid): continue # just want MG films
      text = "("+rawid+") "+cols[titlecolnum]
      normedid = normalizeid(rawid)
      if normedid in gshtinfo:
        print("normed id collision for: "+normedid+" "+gshtinfo[normedid]+" _VS_ "+text)
        gshtinfo[normedid] += " _AND_ "+text
      else:
        gshtinfo[normedid] = text
  print("found "+str(len(gshtinfo))+" total entries")
print("")

print("CORRELATE")
allids = {}
for idstr in mgninfo: allids[idstr] = True
for idstr in gshtinfo: allids[idstr] = True
for idstr in sorted(allids):
  print("\t".join([
    idstr,
    mgninfo[idstr] if idstr in mgninfo else "NotInMGNumerical",
    gshtinfo[idstr] if idstr in gshtinfo else "NotInGSheets"
  ]))
