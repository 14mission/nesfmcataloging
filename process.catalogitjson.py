#!/usr/bin/env python
import json, glob, re

def idnorm(idstr):
  idstr = idstr.lower()
  idstr = re.sub(r'[^\w\s]+','.',idstr)
  idstr = re.sub(r'(\d)\s*\.\s*(\d)',r'\1__DOT__\2',idstr)
  idstr = re.sub(r'([a-z])\s+([a-z])',r'\1__SPACE__\2',idstr)
  idstr = re.sub(r'\W+','',idstr)
  idstr = re.sub(r'__DOT__','.',idstr)
  idstr = re.sub(r'__SPACE__',' ',idstr)
  return idstr

for rawidstr in [ "2025-15-99b", "FOO Bar", "XYZZY 99","PCM.99" ]:
  print(rawidstr + " -> " + idnorm(rawidstr))

# find one json file, read it
jsonfnlist = glob.glob("catalogit*json")
if len(jsonfnlist) != 1: raise Exception("want 1 jsonfn but found "+str(len(jsonfnlist)))
print(f"load {jsonfnlist[0]}")
jsondata = json.load(open(jsonfnlist[0]))

normentobjid2entry = {}

# check for required fields
for entry in jsondata:
  citid = str(entry["CIT ID"])
  if 'Name/Title' in entry:
    citnametitle = str(entry['Name/Title'])
  else:
    citnametitle = "NoCitNameTitle"
  # entry object ID where it's supposed to be?
  if 'Entry/Object ID' in entry:
    citentobjid = entry['Entry/Object ID']
    citentobjidsrc = 'EntObjID'
  # try: Other Names and Numbers -> Other Numbers -> Other Number (may be more than one)
  # look for YYYY.DONOR.ITEM code or an MG code
  # may be preceded by some verbiage
  elif (matchobj := re.search(r'["\']Other Number["\']\s*:\s*["\'](?:Object\s*ID:)?\s*(\d{4}\.\d+\.\d+(?:-?[a-z])?|MG[\.\s]*\d+(?:-?[a-z])?)["\';\s]', str(entry))) != None:
    citentobjid = matchobj.group(1)
    citentobjidsrc = "OtherNumber"
  # no entry object id found
  else:
    citentobjid = "NoCitEntObjID"
    citentobjidsrc = "NONE"
    print("NOID: "+str(entry))
  citshlvcan = str("NotYet")
  # normed entry/objid->entry
  if citentobjidsrc != "NONE":
    normentobjid = idnorm(citentobjid)
    citentrysynopsis = citid+":"+citnametitle
    if citentobjid in normentobjid2entry:
      print("DUPOBJID\t"+normentobjid+"\t"+normentobjid2entry[normentobjid]+"\t"+citentrysynopsis)
    else:
      normentobjid2entry[normentobjid] = citentrysynopsis
  # log what's found
  print("\t".join([
    citid,
    str(citentobjid),
    citentobjidsrc,
    citshlvcan,
    citnametitle
  ]))
