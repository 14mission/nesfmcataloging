#!/usr/bin/env python3
import sys, re, json
from loc_authorities.api import LocAPI

loc = LocAPI()

print("#name\tlabel\tlink\tfilm\tocc\tvariants\tsources")

for ln in sys.stdin:
  ln = ln.strip()
  cols = ln.split("\t")
  name = cols[0]
  revname = re.sub(r'^(.+?)\s+(\w+)\s*$',r'\2, \1',name)

  suggestionlist = loc.suggest(revname,"names")
  if len(suggestionlist) == 0:
    print("\t".join([name,"","","","","",""]))
  else:
    for sugg in suggestionlist:
      label = sugg.label
      link = sugg.uri
      jsonstr = json.dumps(vars(sugg))
      moviethemematch = re.search(r'(?i)(motion.picture|actor|actress|director|film)',jsonstr)
      moviethemematchstr = None if moviethemematch == None else moviethemematch.group()
      variants = []
      sources = []
      occupations = []
      moredata = sugg._data["more"]
      if "variantLabels" in moredata:
        for varlbl in moredata["variantLabels"]:
          variants.append(varlbl)
      if "sources" in moredata:
        for source in moredata["sources"]:
          sources.append(re.sub(r'found\s*:\s*','',source))
      if "occupations" in moredata:
        for occ in moredata["occupations"]:
          occupations.append(occ)
      print("\t".join([
        name,
        str(label),
        str(link),
        str(moviethemematchstr),
        "|".join(occupations),
        "|".join(variants),
        "|".join(sources)
      ])) 
