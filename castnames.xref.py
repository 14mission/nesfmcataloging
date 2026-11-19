#!/usr/bin/env python3
import sys, re, json, os
from loc_authorities.api import LocAPI
import tmdbsimple as tmdb
tmdb.API_KEY = os.getenv('TMDB_API_KEY')

def namenorm(name):
  name = re.sub(r'\.','. ',name)
  name = " ".join(name.split())
  return name

def filmnorm(film):
  film = film.lower()
  film = re.sub(r'[\(\*].*$','',film)
  film = re.sub(r"\'",'',film)
  film = re.sub(r'[^\w\s]',' ',film)
  film = re.sub(r'\b(the|of|a)\b',' ',film)
  film = " ".join(film.split())
  return film

def list2str(list,trunc=None):
  if list == None:
    return "Null"
  elif len(list) == 0:
    return "Empty"
  elif trunc != None and len(list) > trunc:
    return(", ".join([str(item) for item in list[0:trunc]])+"...")
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
      title = filmnorm(title)
      for colnum in namecolnums:
        for name in re.split(r',|\&',cols[colnum]):
          name = namenorm(name)
          if len(name) > 0:
            if name not in name2filmtitles:
              name2filmtitles[name] = {}
            name2filmtitles[name][title] = True

# set up LOC interface
print("set up loc")
loc = LocAPI()

# set up tmdb interface
#print("set up tmdb")
#tmdbsearch = tmdb.Search()
#response = search.person(query="Tom Cruise")

print("ok")
print("")

for ln in sys.stdin:
  ln = ln.strip()
  cols = ln.split("\t")
  name = cols[0]
  name = namenorm(name)
  print("name: "+name)

  # look up in loc
  #print(" query loc")
  revname = re.sub(r'^(.+?)\s+(\w+)\s*$',r'\2, \1',name)
  suggestionlist = loc.suggest(revname,"names")

  # find likely film-related people in loc
  locmatches = []
  locmatchdates = {}
  for sugg in suggestionlist:
    label = sugg.label
    link = sugg.uri
    jsonstr = json.dumps(vars(sugg))
    if re.search(r'(?i)(motion.picture|actor|actress|director|film)',jsonstr):
      #print(jsonstr)
      suggdata = { "label": sugg.label, "uri": sugg.uri, "dates":None }
      datematch = re.search(r'\b((?:18|19)\d\d-19\d\d)\b', suggdata["label"])
      if datematch:
        suggdata["dates"] = datematch.group(1)
        locmatchdates[datematch.group(1)] = True
      locmatches.append(suggdata)

  # look up in tmdb
  #print(" query tmdb")
  tmdbresp = tmdb.Search().person(query=name)
  tmdbmatches = []
  if tmdbresp["results"]:
    for res in tmdbresp["results"]:
      respdata = { "name": res["name"], "original_name": res["original_name"], "dates": None, "id":res["id"], "datematch":False }
      person = tmdb.People(res["id"])
      personinfo = person.info()
      if personinfo == None: personinfo = {}
      respdata["dates"] = (personinfo["birthday"].split("-")[0] if "birthday" in personinfo and personinfo["birthday"] != None else "UNK") + "-" + (personinfo["deathday"].split("-")[0] if "deathday" in personinfo and personinfo["deathday"] != None else "UNK")
      movie_credits = person.combined_credits()
      respdata["credits"] = [filmnorm(movie['title']) for movie in movie_credits['cast'] + movie_credits['crew']]
      respdata["matchingcredits"] = {}
      for title in respdata["credits"]:
        if name in name2filmtitles and title in name2filmtitles[name]:
          respdata["matchingcredits"][title] = True
      if respdata["dates"] in locmatchdates:
        respdata["datematch"]=True
      tmdbmatches.append(respdata)

  #print(name)
  if name in name2filmtitles:
    print(" ourfilms: "+list2str(sorted(name2filmtitles[name])))
  for locmatch in locmatches:
    print(" loc: "+locmatch["label"]+"; "+str(locmatch["dates"])+"; "+locmatch["uri"])
  if len(locmatches) == 0:
    print(" loc: NONE")
  for tmdbmatch in tmdbmatches:
    print(" tmdb: "+tmdbmatch["name"]+"; "+str(tmdbmatch["dates"])+"; "+str(tmdbmatch["id"]))
    print("  datematch: "+str(tmdbmatch["datematch"]))
    print("  matchingfilms: "+list2str(sorted(tmdbmatch["matchingcredits"])))
    print("  allfilms: "+list2str(sorted(tmdbmatch["credits"]),10))
  if len(tmdbmatches) == 0:
    print(" tmdb: NONE")
  print("")
  sys.stdout.flush()
