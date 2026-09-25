#!/usr/bin/env python3
import sys, re, json
from loc_authorities.api import LocAPI

loc = LocAPI()

print("#name\tlabel\tvariants\tlinks\tsources\tothermatches")

for ln in sys.stdin:
  ln = ln.strip()
  cols = ln.split("\t")
  name = cols[0]
  revname = re.sub(r'^(.+?)\s+(\w+)\s*$',r'\2, \1',name)

  matchedlabels = [] # hopefully just one!
  matchuris = [] # same, but same number as above anyway
  variantlabels = [] # all variants from all matches, which again is hopefully just one
  sources = [] # first source for each match (though there are likely >1 for each)
  outofscopesuggestions = [] # other folks with the same name, log various things

  #print(f"LOOKUP: {revname}")

  suggestionlist = loc.suggest(revname,"names")
  for sugg in suggestionlist:
    #print(" SUGGESTION")
    jsonstr = json.dumps(vars(sugg))
    moredata = sugg._data["more"]
    # movie-related suggestion
    if re.search(r'(?i)(motion.picture|actor|actress|director|film)',json.dumps(vars(sugg))):
      #print("  MOTION_PICTURE_SUGGESTION")
      #print("  uri="+sugg.uri)
      #print("  label="+sugg.label)
      matchedlabels.append(sugg.label)
      matchuris.append(sugg.uri)
      if "variantLabels" in moredata:
        for varlbl in moredata["variantLabels"]:
          variantlabels.append(varlbl)
        #print("  variantlabels="+"|".join(moredata["variantLabels"]))
      if "sources" in moredata and len(moredata["sources"]) > 0:
        sources.append(re.sub(r'found\s*:\s*','',moredata["sources"][0]))
    # other suggestions
    else:
      outofscopesuggestions.append("label="+sugg.label)
      if "occupations" in moredata and len(moredata["occupations"]) > 0:
        outofscopesuggestions[-1] += "; occ="+"/".join(moredata["occupations"])
      if "sources" in moredata and len(moredata["sources"]) > 0:
        outofscopesuggestions[-1] += "; src="+re.sub(r'found\s*:\s*','',moredata["sources"][0])
  print("\t".join([name, "|".join(matchedlabels), "|".join(variantlabels), "|".join(matchuris), "|".join(sources), "|".join(outofscopesuggestions)]))
