#!/usr/bin/env python3
import sys, re, json, os
from loc_authorities.api import LocAPI
import tmdbsimple as tmdb
tmdb.API_KEY = os.getenv('TMDB_API_KEY')

#usage: tsv file exported from spreadsheets as single arg, stdin names to investigate
if len(sys.argv) != 2:
  raise Exception("need one arg, tsv from spreadsheet, to get name/film mappings")

filmtsvfn = sys.argv[1]

name2filmtitles = {}
print(f"get name/film mappings from {filmtsvfn}")
namecolnums = []
titlecolnum = None
maxcolneeded = 0
if True:
 filmtsvh = open(filmtsvfn)
 for ln in filmtsvh:
   cols = ln.split("\t")
   if titlecolnum == None:
     for colnum, colname in enumerate(cols):
       #print(f"col {colname}")
       if re.search(r'(?i)(filed.*dir.*star|writer|director|^star|cast)',colname):
         print(f"namecol: {colname}")
         namecolnums.append(colnum)
         if colnum >= maxcolneeded:
           maxcolneeded = colnum
       elif re.search(r'(?i)(^title)',colname):
         print(f"titlecol: {colname}")
         titlecolnum = colnum
         if colnum >= maxcolneeded:
           maxcolneeded = colnum
     if titlecolnum == None: raise Exception("no title col found")
     if len(namecolnums) < 2: raise Exception("too few name cols")
   elif len(cols) >= maxcolneeded:
     title = cols[titlecolnum]
     title = re.sub(r'\(.*?\)',' ',title)
     title = re.sub(r'(?i)\s*,\s*the.*$','',title)
     title = re.sub(r'\*\S+',' ',title)
     title = " ".join(title.split())
     for colnum in namecolnums:
       for name in cols[colnum].split(","):
         name = " ".join(name.split())
         if len(name) > 0:
           if name not in name2filmtitles:
             name2filmtitles[name] = []
           name2filmtitles[name].append(title)
         #print(f"map: {name} -> "+cols[titlecolnum])
#print("mappings:")
#for name in sorted(name2filmtitles):
#  print(name+": "+",".join(name2filmtitles[name]))

# set up LOC interface
print("set up loc")
loc = LocAPI()

# set up tmdb interface
print("set up tmdb")
tmdb = tmdb.Search()
#response = search.person(query="Tom Cruise")

print("ok")

for ln in sys.stdin:
  ln = ln.strip()
  cols = ln.split("\t")
  name = cols[0]
  print("name: "+name)

  # look up in loc
  print(" query loc")
  revname = re.sub(r'^(.+?)\s+(\w+)\s*$',r'\2, \1',name)
  suggestionlist = loc.suggest(revname,"names")

  # find likely film-related people in loc
  locfilmmatches = []
  for sugg in suggestionlist:
    label = sugg.label
    link = sugg.uri
    jsonstr = json.dumps(vars(sugg))
    if re.search(r'(?i)(motion.picture|actor|actress|director|film)',jsonstr):
      #print(jsonstr)
      suggdata = { "label": sugg.label, "uri": sugg.uri }
      datematch = re.search(r'\b((?:18|19)\d\d-19\d\d)\b', suggdata["label"])
      suggdata["dates"] = (datematch.group(1) if datematch else None)
      locfilmmatches.append(suggdata)

  # look up in tmdb
  print(" query tmdb")
  tmdbresp = tmdb.person(query=name)

  print(name+"\n"
    + " ourfilms="+(",".join(name2filmtitles[name] if name in name2filmtitles else "None"))+"\n"
    + " locmatches="+(",".join([str(m) for m in locfilmmatches]) if len(locfilmmatches) else "None")+"\n"
    + " tmdb="+str(tmdbresp)+"\n"
  )
