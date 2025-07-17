#!/usr/bin/env python3
import json, glob, re, sys

# to run this script:
# export all films from CatalogIt, include all fields, name file "catalogit.allfilms.allfields.json"
# then just run this script, it looks for that file and reads it

# what it does:
# - checks that each record has a valid ObjectId; they can be recorded in various fields
# - checks for collisions, multiple entries with the same ObjectId

# things to look for in output
# - "NOOBJID" : records where we couldn't find any ObjId
# - "DUPOBJID" : duplicate normalized ObjId found in multiple records

# this function irons out superficial differences between ID's that don't really matter
def idnorm(idstr):
  # lowercase
  idstr = idstr.lower()
  # turn all puncs into dot
  idstr = re.sub(r'[^\w\s]+','.',idstr)
  # preserve dot between digs. might be space, too
  idstr = re.sub(r'(?<=\d)\s*\.\s*(?=\d)',r'__DOT__',idstr)
  # preserve space between letters
  idstr = re.sub(r'(?<=[a-z])\s+(?=[a-z])',r'__SPACE__',idstr)
  # clobber any remaining nonalphadig
  idstr = re.sub(r'\W+','',idstr)
  # restore preserved dot and space
  idstr = re.sub(r'__DOT__','.',idstr)
  idstr = re.sub(r'__SPACE__',' ',idstr)
  return idstr

# print some sample ID normalization
for rawidstr in [ "2025-15-99b", "FOO Bar", "XYZZY 99","PCM.99", "2012.3.232.b", "2012-3.232-B" ]:
  print(rawidstr + " -> " + idnorm(rawidstr))

# read spreadsheet tsv's
# find object id's (col labeled Accession Number)
# map to titles
tsvnormentobjid2title = {}
numunkobjid = 0
for tsvfn in glob.glob("NESFM*tsv"):
  print("spreadsheet tsv: "+tsvfn)
  if "videos" in tsvfn:
    print("skip")
    continue
  tsvin = open(tsvfn)
  objidcolnum, titlecolnum = None, None
  for ln in tsvin:
    cols = ln.split("\t")
    if objidcolnum == None:
      for colnum in range(len(cols)):
        if "Accession Number" in cols[colnum]:
          objidcolnum = colnum
        elif "Title" in cols[colnum]:
          titlecolnum = colnum
      print("objidcolnum = "+str(objidcolnum)+"; titlecolnum="+str(titlecolnum))
      if objidcolnum == None:
        print("no accession num: "+",".join(cols))
        sys.exit(1)
      elif titlecolnum == None: 
        print("no title: "+",".join(cols))
        sys.exit(1)
    else:
      normobjid = idnorm(cols[objidcolnum])
      if "unknown" in normobjid.lower():
        numunkobjid += 1
      else:
        tsvnormentobjid2title[normobjid] = cols[titlecolnum]
print("mapped "+str(len(tsvnormentobjid2title))+" objids")
print("unknown: "+str(numunkobjid))

# find one json file, read it
jsonfnlist = glob.glob("catalogit*json")
if len(jsonfnlist) != 1: raise Exception("want 1 jsonfn but found "+str(len(jsonfnlist)))
print(f"load {jsonfnlist[0]}")
jsondata = json.load(open(jsonfnlist[0]))

# keep track of mappings of normalized ID's to records we have seen
# this is so we can report on collisions
citnormentobjid2entry = {}

# write outputs
outtsv = open("process.catalogitjson.out.tsv","w")
outlog = open("process.catalogitjson.out.log","w")

# header for output
print("\t".join([
  "CitID",
  "CitEntObjId",
  "CitEntObjIdSrc",
  "CitShelfCanCode",
  "CitNameTitle",
  "TsvNameTitle",
]), file=outtsv)

# for all entries
for entry in jsondata:
  # CatalogIt's own ID, which is guaranteed to be unique
  citid = str(entry["CIT ID"])
  # entry should have a title
  if 'Name/Title' in entry:
    citnametitle = str(entry['Name/Title'])
  else:
    citnametitle = "NoCitNameTitle"
  # let's ignore video entries
  if re.search(r'(?i)\b(vhs|dvd|blu-?ray)\b',str(entry)) != None:
    print("SKIPVIDEO: "+str(entry), file=outlog)
    continue
  # ObjectId: first look where it's suposed to be, in the "Entry/Object ID" field
  elif 'Entry/Object ID' in entry:
    citentobjid = entry['Entry/Object ID']
    citentobjidsrc = 'EntObjID'
  # try: Other Names and Numbers -> Other Numbers -> Other Number (may be more than one)
  # look for YYYY.DONOR.ITEM code or an MG code
  # may be preceded by some verbiage
  elif (matchobj := re.search(r'["\']Other Number["\']\s*:\s*["\'](?:Object\s*ID:)?\s*(\d{4}\.\d+\.\d+(?:-?[a-z])?|MG[\.\s]*\d+(?:-?[a-z])?|L\d+)["\';\s]', str(entry))) != None:
    citentobjid = matchobj.group(1)
    citentobjidsrc = "OtherNumber"
  # no entry object id found
  else:
    citentobjid = "NoCitEntObjID"
    citentobjidsrc = "NONE"
    print("NOOBJID: "+str(entry), file=outlog)
  # shelving/can code from CatalogIt -- not doing that yet
  citshlvcan = str("NotYet")
  # normed entry/objid->entry
  dupobjid = False
  normentobjid = None
  if citentobjidsrc != "NONE":
    normentobjid = idnorm(citentobjid)
    citentrysynopsis = citid+":"+citnametitle
    if citentobjid in citnormentobjid2entry:
      print("DUPOBJID\t"+normentobjid+"\t"+citnormentobjid2entry[normentobjid]+"\tVS\t"+citentrysynopsis,file=outlog)
      dupobjid = True
    else:
      citnormentobjid2entry[normentobjid] = citentrysynopsis
  # log what's found
  print("\t".join([
    citid,
    str(citentobjid),
    citentobjidsrc + ("DUP" if dupobjid else ""),
    citshlvcan,
    citnametitle,
    tsvnormentobjid2title[normentobjid] if normentobjid in tsvnormentobjid2title else "NoMatch"
  ]), file=outtsv)
