#!/usr/bin/env python3
import sys,os,re

# later we will make this a fatal error
def badrow(msg,logf):
  print("BAD ROW: "+msg,file=logf)
  print("BAD ROW: "+msg)

# for importing spreadsheets into catalogit
# see notes in doc "Mapping NESFM Silent Film Archive spreadsheet to catalog it"

# rename exported spreadsheets like this: ls NESFM\ Silent\ Film\ Achive\ -\ *tsv | perl -ne 's/\s+$//gs; my $origfn = $_; my $newfn = $origfn; $newfn =~ s/.* - /nesfm.archive./; $newfn =~ s/ /_/g; $newfn =~ s/&/and/g; $newfn = lc $newfn; print "mv \"$origfn\" $newfn\n"' | sh

intsvlist = []
av = sys.argv[1:]
ac = 0
while ac < len(av):
  if av[ac] == "-h": print("usage: "+sys.argv[0]+" -h(elp) inputfiles*tsv -o outputfile.tsv")
  elif av[ac][0] == "-": raise Exeption("unkflag: "+av[ac])
  else: intsvlist.append(av[ac])
  ac += 1

# columns we should create
# columns that should be in output
# format of rows below is output-column-name, flags, input-column-name-pattern
#  note: / can mean either hierarchy field arrangement, or just "aka" in a field name
#  also: a colon in and outcol name means CIt field is an array, with label/vals, and the bit after colon is a label
# note on flags:
#  - means none
#  * mark with a * in output, meaning should be manually edited
#  e ok for the field to be empty
#  m ok for the field to be missing entirely (not in the input spreadsheet at all)
#  u if field is empty, fill with explicit UNKNOWN
#  r field will be filled by a rule
# note on patterns:
#  these are matched agains the column headers of the input files, from google spreadsheets
#  these are regular expressions
#  they are matched case-insensitively
#  they are matched at the beginning
#  they don't have to match all the way to the end
outcols = []
hdrpats = {}
starcols = {}
okunkcols = {}
okemptycols = {}
okmissingcols = {}
rulefillcols = {}
for row in [ 
  r'objid u Acc?ession\s+Num', # unk not actually ok
  r'name/title - Title',
  r'shelvingcode u Shelving|Bartel\s*-*\s*Thomsen\sFilm\sCode',
  r'location u Film\sRack',
  r'collection em (comedy\s+)?Series',
  r'condition/notes:pq e p\s*q\b',
  r'motion_picture_details/production_date/date u prod.*year',
  r'made/created/notes:Re-Issue_Year e re\W*issue.*year',
  r'motion_picture_details/cast *u star\W*s\W*',
  r'motion_picture_details/director *u director',
  r'motion_picture_details/producer/publisher *u produc(er|tion\sco)',
  r'motion_picture_details/writer *em writer',
  r'relationships/related_person_or_organization/notes:Original_Distributor u distrib.*orig',
  r'relationships/related_person_or_organization/notes:Re-Issue_Distributor u distrib.*re\W*issue',
  r'relationships/related_places/notes:Print_Exhibition_Country e print\sexhibition\scountry',
  r'made/created/place e country',
  r'motion_picture_details/film_stock u film\sstock',
  r'motion_picture_details/length u film\slength',
  r'motion_picture_details/sound/sound_notes:Language u language', # actually probably NOT sound; =titles
  r'motion_picture_details/sound/film_sound *u sound\strack',
  r'motion_picture_details/sound/sound_notes:Type r NOSOURCECOLUMN', # populated from "sound track"
  r'motion_picture_details/frame_rate me NOSOURCECOLUMN',
  r'aspect_ratio - aspect\sratio.*film\sformat', # rules to extract fps and gauge from aspect ratio
  r'motion_picture_details/film_gauge/format r NOSOURCECOLUMN',
  r'motion_picture_details/color_characteristics *u film\scolor',
  r'parts/parts - film\sreels', # reels, revisit?
  r'general_notes/note:Best_Quality_DVD_Release um dvd\s+release',
  r'general_notes/note:Best_Quality_Blu-ray_Release um blu\W*ray\s+release',
  r'general_notes/note:Best_Quality_Blu-ray_or_DVD_Release um best\squality.*dvd.*blu.*ray.*release',
  r'general_notes/note:Stereotypes u stereotypes',
  r'general_notes/note *u notes', # label needed
  r'acquisition/source u don(at)?or|blackhawk\sassets|assett?s$', 
  ]:
  cols = row.split()
  if len(cols) != 3: raise Exception("misformatted label spec: "+row)
  label, flags, pattern = cols
  outcols.append(label)
  hdrpats[label] = pattern
  for c in flags:
    if c == '*':
      starcols[label] = True
    elif c == 'u':
      okunkcols[label] = True
    elif c == 'm':
      okmissingcols[label] = True
    elif c == 'e':
      okemptycols[label] = True
    elif c == 'r':
      rulefillcols[label] = True
    elif c != '-':
      raise Exception("unexpected flag char "+c)

# process all input files specified on the command line
for intsv in intsvlist:

  # ignore certain files: "deaccessioned", and files written by this program
  if re.match(r'(?i).*(de\W*a[cs]*se[cs]+ion|4cit)',intsv):
    print(f"SKIP {intsv}")
    continue

  # start reading this fiel
  print(f"read {intsv}")
  inh = open(intsv)
  lnum = 0

  # output file
  outfn = re.sub(r'\.\w+$','',intsv)
  outfn += ".4cit.tsv"
  print(f"write output to {outfn}")
  outh = open(outfn,"w")
  print("\t".join(outcols)+"\tsource\tline",file=outh)

  # log file
  logfn = re.sub(r'\.\w+$','',intsv)
  logfn += ".4cit.log"
  print(f"write logs to {logfn}")
  logh = open(logfn,"w")

  # short name of file to put in output
  source = intsv
  source = re.sub(r'^.*- *','',source)
  source = re.sub(r'\.tsv$','',source)

  # we will look at header row and figure out what input col maps to what output col
  colmap = {}
  for field in outcols:
    colmap[field] = None

  # read all lines
  for ln in inh:
    lnum += 1
    lncols = ln.split("\t")
    lncols[-1] = lncols[-1].strip()

    # header line?
    # map input cls to output cols
    if colmap["objid"] == None:
      # map input cols to output cols
      for colnum, colstr in enumerate(lncols):
        for outcol in outcols:
          if re.match(r'(?i)^('+hdrpats[outcol]+')',colstr): colmap[outcol] = colnum
      # check that all required output cols were matched
      for field in sorted(colmap.keys()):
        if colmap[field] == None:
          if field in okmissingcols or field in rulefillcols:
            print(field + "=None")
          else:
            raise Exception("no \""+field+"\" col found in \""+intsv+"\": HDRCOLS="+",".join(lncols))
        else:
          print(field + "=" + str(colmap[field]) + "=" + lncols[colmap[field]], file=logh)
      # check that nothing was mapped unexpectedly
      unexpectedoutputcols = [colname for colname in colmap.keys() if colname not in outcols]
      if len(unexpectedoutputcols) > 0:
        raise Exception("unexpected output column mapping to: "+", ".join(unexpectedoutputcols))
      # check that all input cols were mapped, except ones explicitly known to be unneeded
      unmappedinputcols = [colnum for colnum in range(len(lncols)) if colnum not in colmap.values() and re.search(r'(?i)(created \d+\/|updated \d+\/|catalog\W*it|filed by director or star|sorted by director or catagory|^\s*$)',lncols[colnum]) == None]
      if len(unmappedinputcols) > 0:
        raise Exception("unmapped input cols: "+", ".join(lncols[colnum] for colnum in unmappedinputcols))

      # rest of loop is for regular data lines
      continue

    # film not actually in archive?
    if re.search(r'(?i)NO prints in Archive',ln) != None:
      continue

    # section divider line? print it but then ignore
    # other ignorable types too
    if len([col for col in lncols if col != None and len(col.strip())>0]) <= 2 or re.search(r'(?i)(HATS OFF IS A LOST FILM|no prints in archive|NO film prints.+DVD)',ln):
      print(f"skip line: {lnum}: "+ln.strip(), file=logh)
      continue

    # regular line.  make sure all required fields filled
    # some fields can be empty, then we put UNKNOWN
    outcolvals = {}
    isbadrow = False
    for colname in outcols:
      if colname not in colmap or colmap[colname] == None:
        continue
      elif lncols[colmap[colname]] == None or len(lncols[colmap[colname]].strip()) == 0:
        # some cols allowed to be empty
        if colname in okemptycols:
          outcolvals[colname] = None
        # for some cols, we just specify UNKNOWN
        elif colname in okunkcols:
          print(f"empty (use UNKNOWN) {colname} in line {lnum}: "+ln.strip(), file=logh)
          outcolvals[colname] = "UNKNOWN"
        # for others, an empty value is a fatal error
        else:
          print(f"empty (NOTALLOWED) {colname} in line {lnum}:"+ln.strip(), file=logh)
          badrow(f"empty (NOTALLOWED) {colname} in line {lnum}:"+ln.strip(),logh)
          isbadrow = True
      else:
        outcolvals[colname] = lncols[colmap[colname]].strip()
    # in case badrow() just warns
    if isbadrow:
      continue

    # special rules:

    # extract film gauge from title: can be like **35mm** or (35mm)
    aspect_ratio_title_match = re.match(r'(.+?)\s(?:\*\*|\()(\d+)(mm)(?:\*\*|\))\s*$', outcolvals["name/title"])
    if aspect_ratio_title_match != None:
      coretitle = aspect_ratio_title_match.group(1)
      titlefilmgauge = aspect_ratio_title_match.group(2) + aspect_ratio_title_match.group(3)
      if outcolvals["aspect_ratio"] != None and re.search(r'\d+\s*mm', outcolvals["aspect_ratio"]) != None and re.search(titlefilmgauge,outcolvals["aspect_ratio"]) == None:
        badrow("inconsistent film gauge: title=\""+outcolvals["title"]+"\" vs aspect ratio=\""+outcolvals["aspect_ratio"]+"\"",logh)
        continue
      outcolvals["motion_picture_details/film_gauge/format"] = titlefilmgauge
      outcolvals["name/title"] = coretitle
      if outcolvals["aspect_ratio"] == None:
        outcolvals["aspect_ratio"] = "UNKNOWN"

    # extract frame rate from aspect ratio, if present
    if outcolvals["aspect_ratio"] != None:
      apect_ratio_and_frame_rate_match = re.match(r'(?i)^(.+?)\s+(\d+\s*fps)\s*$', outcolvals["aspect_ratio"])
      if apect_ratio_and_frame_rate_match != None:
        outcolvals["aspect_ratio"] = apect_ratio_and_frame_rate_match.group(1)
        outcolvals["motion_picture_details/frame_rate"] = apect_ratio_and_frame_rate_match.group(2).upper()

    # extract film gauge from aspect ratio
    if outcolvals["aspect_ratio"] != None:
      apect_ratio_and_film_gauge_match = re.match(r'^(.+?)\s+(\d+(?:\.\d+)?\s*mm)(\s*.*?)$', outcolvals["aspect_ratio"])
      if apect_ratio_and_film_gauge_match != None:
        outcolvals["aspect_ratio"] = apect_ratio_and_film_gauge_match.group(1) + apect_ratio_and_film_gauge_match.group(3).strip()
        outcolvals["motion_picture_details/film_gauge/format"] = apect_ratio_and_film_gauge_match.group(2)

    # if film gauge still not filled, that's a problem
    if "motion_picture_details/film_gauge/format" not in outcolvals or outcolvals["motion_picture_details/film_gauge/format"] == None:
      badrow(f"no film gauge found in line {lnum}: "+ln.strip(),logh)
      continue

    # country normalization
    for countryfield in [ "relationships/related_places/notes:Print_Exhibition_Country", "made/created/place" ]:
      if countryfield in outcolvals and outcolvals[countryfield] != None:
        outcolvals[countryfield] = re.sub(r'^U\W*S\W*A\W*','United States',outcolvals[countryfield])
        outcolvals[countryfield] = re.sub(r'^U\W*K\W*','United Kingdom',outcolvals[countryfield])
        outcolvals[countryfield] = re.sub(r'\bMex\.','Mexico',outcolvals[countryfield])
        outcolvals[countryfield] = " ".join(outcolvals[countryfield].split())
        outcolvals[countryfield] = outcolvals[countryfield].title()

    # sound normalization
    if "motion_picture_details/sound/film_sound" in outcolvals and outcolvals["motion_picture_details/sound/film_sound"] != None:
      soundval = outcolvals["motion_picture_details/sound/film_sound"]
      if re.match(r'(?i)^silent$',soundval):
        soundval = "si."
      else:
        outcolvals["motion_picture_details/sound/sound_notes:Type"] = soundval
        soundval = "sd."
      #print(outcolvals["motion_picture_details/sound/film_sound"]+" -> "+soundval+" + "+(outcolvals["motion_picture_details/sound/sound_notes:Type"] if "motion_picture_details/sound/sound_notes:Type" in outcolvals else ""))
      outcolvals["motion_picture_details/sound/film_sound"] = soundval

    # TBD: handle serieses
    # if series col, and filled, prefix to title
    # if "series" in colmap and len(lncols[colmap["series"]].strip()):
    #  lncols[colmap["title"]] = lncols[colmap["series"]].strip() + ": " + lncols[colmap["title"]]

    # cols allowed to be empty get explicit "None" for now, may change to empty string later
    #novalstr = "None"
    novalstr = ""
    print("\t".join(outcolvals[colname] if colname in outcolvals and outcolvals[colname] != None else novalstr for colname in outcols)+"\t"+source+"\t"+str(lnum), file=outh)
