#!/usr/bin/env python3
import sys, re, json, os
from loc_authorities.api import LocAPI
import tmdbsimple as tmdb
tmdb.API_KEY = os.getenv('TMDB_API_KEY')

def list2str(list):
  if list == None:
    return "Null"
  elif len(list) == 0:
    return "Empty"
  else:
    return(", ".join([str(item) for item in list]))

#usage: tsv file exported from spreadsheets as single arg, stdin names to investigate
if len(sys.argv) < 2:
  raise Exception("need one arg, tsv from spreadsheet, to get name/film mappings")

name2filmtitles = {}
for filmtsvfn in sys.argv[1:]:
  print(f"get name/film mappings from {filmtsvfn}")
  namecolnums = []
  titlecolnum = None
  maxcolneeded = 0
  filmtsvh = open(filmtsvfn)
  for ln in filmtsvh:
    cols = ln.split("\t")
    if titlecolnum == None:
      for colnum, colname in enumerate(cols):
        if re.search(r'(?i)(filed.*dir.*star|writer|director|^star|cast)',colname):
          print(f" namecol: {colname}")
          namecolnums.append(colnum)
          if colnum >= maxcolneeded:
            maxcolneeded = colnum
        elif re.search(r'(?i)(^title)',colname):
          print(f" titlecol: {colname}")
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

# set up LOC interface
print("set up loc")
loc = LocAPI()

# set up tmdb interface
#print("set up tmdb")
#tmdbsearch = tmdb.Search()
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
  tmdbresp = tmdb.Search().person(query=name)
  tmdbmatches = []
  if tmdbresp["results"]:
    for res in tmdbresp["results"]:
      respdata = { "name": res["name"], "original_name": res["original_name"], "dates": None, "id":res["id"] }
      personinfo = tmdb.People(res["id"]).info()
      respdata["dates"] = personinfo["birthday"].split("-")[0] + "-" + personinfo["deathday"].split("-")[0]
      tmdbmatches.append(respdata)
       

  print(name+"\n"
    + " ourfilms="+list2str(name2filmtitles[name] if name in name2filmtitles else ["None"])+"\n"
    + " locmatches="+list2str(locfilmmatches)+"\n"
    + " tmdbmatches="+list2str(tmdbmatches)+"\n"
  )
