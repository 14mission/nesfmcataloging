#!/usr/bin/env python3
import sys, re, json
from loc_authorities.api import LocAPI

loc = LocAPI()

for ln in sys.stdin:
  ln = ln.strip()
  cols = ln.split("\t")
  name = cols[0]
  revname = re.sub(r'^(.+?)\s+(\w+)\s*$',r'\2, \1',name)
  print(f"LOOKUP: {revname}")

  suggestionlist = loc.suggest(revname,"names")
  for sugg in suggestionlist:
    print(" SUGGESTION")
    jsonstr = json.dumps(vars(sugg))
    moredata = sugg._data["more"]
    if re.search(r'(?i)(motion.picture|actor|actress|director|film)',json.dumps(vars(sugg))):
      print("  MOTION_PICTURE_SUGGESTION")
      print("  uri="+sugg.uri)
      print("  label="+sugg.label)
      if "variantLabels" in moredata:
        print("  variantlabels="+", ".join(moredata["variantLabels"]))
    elif "occupations"  in moredata: 
      print("  NON-MOVIE-OCCUPATION: "+", ".join(moredata["occupations"]))
