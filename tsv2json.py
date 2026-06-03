#!/usr/bin/env python
import sys, re, json

for tsvfn in sys.argv[1:]:
  print(f"read {tsvfn}")
  inh = open(tsvfn)
  jsonfn = re.sub(r'\.\w+$','',tsvfn)+".json"
  print(f"write {jsonfn}")
  outh = open(jsonfn,"w")
  print("[",file=outh)
  colnames = None
  for ln in inh:
    cols = ln.split("\t")
    cols[-1] = cols[-1].strip()
    if colnames == None:
      cols[0] = re.sub(r'^#','',cols[0])
      colnames = cols
      print("cols: "+", ".join(colnames))
      continue
    if len(cols) != len(colnames):
      raise Exception("expected "+str(len(colnames))+" but found "+str(len(cols))+" in: "+ln)
    record = {}
    for colname, colval in zip(colnames,cols):
      # do not include empty values
      if len(colval.strip()) == 0:
        continue
      # do not include debugging cols
      elif colname in ["source","line"]:
        continue

      # replace underscore with whitespace in attrib name
      attribname = re.sub(r'_',' ',colname)
      attribpath = re.sub(r':','/',attribname).split("/")
      attribpath = [re.sub(r'\|','/',chunk) for chunk in attribpath]
      recordnode = record
      for treelevel in range(len(attribpath)-1):
        if attribpath[treelevel] not in recordnode:
          recordnode[attribpath[treelevel]] = {}
        recordnode = recordnode[attribpath[treelevel]]
      recordnode[attribpath[-1]] = colval
      



      # if colname contains ":", this is a multi-value attrib, and each val has a key; bit after colon is key
      #keynameformultivalattrib = None
      #if ":" in attribname:
      #  attribname, keynameformultivalattrib = attribname.split(":")

      #if keynameformultivalattrib == None:
      #  record[attribname] = colval
      #else:
      #  if attribname not in record:
      #    record[attribname] = []
      #    keyval = {}
      #    keyval[keynameformultivalattrib] = colval
      #    record[attribname].append(keyval)
      #           # {keynameformultivalattrib,colval})

    # format record as json, print
    jsonrecord = json.dumps(record)
    print(jsonrecord+",",file=outh)

  print("]",file=outh)
