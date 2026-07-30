#!/usr/bin/env python3
import sys,os,re
import json
import csv

# later we will make this a fatal error
def badrow(msg,logf):
  print("BAD ROW: "+msg,file=logf)
  print("BAD ROW: "+msg)
  return 1

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
#  also: if there is a colon, the bit after the colon should be prefixed to the value string
# note on flags:
#  - means none
#  * mark with a * in output, meaning should be manually edited
#  e ok for the field to be empty
#  m ok for the field to be missing entirely (not in the input spreadsheet at all)
#  u if field is empty, fill with explicit UNKNOWN
#  r field will be filled by a rule
#  c means split on comma
# note on patterns:
#  these are matched against the column headers of the input files, from google spreadsheets
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
commasplitcols = {}
objidcolname = r'Entry/Object_ID'
accnumcolname = r'Acquisition/Accession'
for row in [ 
  objidcolname+r' u Acc?ession\s+Num', # unk not actually ok
  accnumcolname+r' r NOSOURCECOLUMN', # truncated obj id
  r'Name/Title - Title',
  r'Other_Names_and_Numbers/Other_Numbers:Shelving u Shelving|Bartel\s*-*\s*Thomsen\sFilm\sCode',
  r'Other_Names_and_Numbers/Other_Numbers:Old_Object_ID r NOSOURCECOLUMN',
  r'Location/Location u Film\sRack',
  r'Collection em (comedy\s+)?Series',
  r'Condition/Overall_Condition e p\s*q\b', # note from nk: original spec was Condition/Notes:PQ but not in CatalogIt schema
  r'Motion_Picture_Details/Production_Date/Date u prod.*year',
  r'Made/Created/Notes:Re-Issue_Year e re\W*issue.*year',
  r'Motion_Picture_Details/Cast *uc star\W*s\W*',
  r'Motion_Picture_Details/Director *u director', # note: flags should be *uc, but multivals not supported by CatalogIt yet
  r'Motion_Picture_Details/Producer/Publisher *u produc(er|tion\sco)',
  r'Motion_Picture_Details/Writer *emc writer',
  r'Relationships/Related_Person_or_Organization/Notes:Original_Distributor e distrib.*orig',
  r'Relationships/Related_Person_or_Organization/Notes:Re-Issue_Distributor e distrib.*re\W*issue',
  r'Relationships/Related_Places/Notes:Print_Exhibition_Country e print\sexhibition\scountry',
  r'Made/Created/Place e country',
  r'Motion_Picture_Details/Film_Stock e film\sstock',
  r'Motion_Picture_Details/Length e film\slength',
  r'Motion_Picture_Details/Sound/Sound_Notes:Language e language', # actually probably NOT sound; =titles
  r'Motion_Picture_Details/Sound/Film_Sound *u sound\strack',
  r'Motion_Picture_Details/Sound/Sound_Notes:Type r NOSOURCECOLUMN', # populated from "sound track"
  r'Motion_Picture_Details/Frame_Rate me NOSOURCECOLUMN',
  r'Aspect_Ratio r aspect\sratio.*film\sformat', # rules to extract fps and gauge from aspect ratio
  r'Motion_Picture_Details/Film_Gauge/Format r NOSOURCECOLUMN',
  r'Motion_Picture_Details/Color_Characteristics *e film\scolor',
  r'Parts/Parts - Film\sReels', # reels, revisit?
  r'General_Notes e notes',
  r'General_Notes:Best_Quality_DVD_Release em dvd\s+release',
  r'General_Notes:Best_Quality_Blu-ray_Release em blu\W*ray\s+release',
  r'General_Notes:Best_Quality_Blu-ray_or_DVD_Release em best\squality.*dvd.*blu.*ray.*release',
  r'General_Notes:Stereotypes_or_Content_Issues em stereotypes',
  r'General_Notes:Aperture_Image_Format r NOSUCHCOLUMN',
  r'General_Notes:General r NOSUCHCOLUMN',
  r'Acquisition/Accession/Source_or_Donor u don(at)?or|blackhawk\sassets|assett?s$', 
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
    elif c == 'c':
      commasplitcols[label] = True
    elif c != '-':
      raise Exception("unexpected flag char "+c)
  # cols with colon will not be printed directly, they'll be mapped into cols with base name before colon
  # so we'll define cols with base name, to be filled by rule
  if ":" in label:
    beforecolon = re.sub(r':.*$','',label)
    if beforecolon not in outcols:
      outcols.append(beforecolon)
      hdrpats[beforecolon] = "NOSOURCECOLUMN"
      rulefillcols[beforecolon] = True

# for assigning custom object id nums for MG's
objid_base_seen = {}

# avoid objid and shelvingcode collisions
objid_seen = {}
shelvingcode_seen = {}

# objid's already in use
objid_incit = {}
citobjidfh = open("existing.catalogit.objectids.txt")
for ln in citobjidfh:
  objid_incit[ln.strip().lower()] = True

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
  outfn += ".4cit.csv"
  print(f"write output to {outfn}")
  outh = csv.writer(open(outfn,"w"))
  hdrcols = [colname for colname in outcols if ":" not in colname]
  hdrcols.append("Tags")
  hdrcols.append("linenum")
  outh.writerow(hdrcols)

  # log file
  logfn = re.sub(r'\.\w+$','',intsv)
  logfn += ".4cit.log"
  print(f"write logs to {logfn}")
  logh = open(logfn,"w")

  # short name of file to put in output
  source = intsv
  source = re.sub(r'^.*- *','',source)
  source = re.sub(r'\.tsv$','',source)
  source = re.sub(r'^nesfm\.archive\.','',source)

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
    if colmap[objidcolname] == None:
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
      print(f"skip line: {lnum}: "+ln.strip(), file=logh)
      continue

    # section divider line? print it but then ignore
    # other ignorable types too
    if len([col for col in lncols if col != None and len(col.strip())>0]) <= 2 or re.search(r'(?i)(HATS OFF IS A LOST FILM|no prints in archive|NO film prints.+DVD)',ln):
      print(f"skip line: {lnum}: "+ln.strip(), file=logh)
      continue

    # regular line. make sure all required fields filled
    # some fields can be empty, then we put UNKNOWN
    outcolvals = {}
    colstoberulefilled = {}
    isbadrow = 0
    for colname in outcols:
      if colname not in colmap or colmap[colname] == None:
        continue
      # various ways of being "empty"
      elif lncols[colmap[colname]] == None or len(lncols[colmap[colname]].strip()) == 0 or re.match(r'(?i)^\W*(unknown|20xx\.xx\.xx)\W*$',lncols[colmap[colname]]):
        # some cols allowed to be empty
        if colname in okemptycols:
          outcolvals[colname] = None
        # for some cols, we just specify UNKNOWN
        elif colname in okunkcols:
          print(f"empty (use UNKNOWN) {colname} in line {lnum}: "+ln.strip(), file=logh)
          outcolvals[colname] = "UNKNOWN"
        # if col is empty and is to be filled by a rule, put it on list of cols to check for later
        elif colname in rulefillcols:
          outcolvals[colname] = None
          colstoberulefilled[colname] = True
        # for others, an empty value is a fatal error
        else:
          print(f"empty (NOTALLOWED) {colname} in line {lnum}:"+ln.strip(), file=logh)
          isbadrow += badrow(f"empty (NOTALLOWED) {colname} in line {lnum}:"+ln.strip(),logh)
      # pipe char will cause problems later
      elif "|" in lncols[colmap[colname]]:
        raise Exception(f"pipe char in line {lnum}: "+ln.strip())
      # regular valid value
      else:
        outcolvals[colname] = lncols[colmap[colname]].strip()

    # special rules:

    # handling of MG object ID's
    # chop off leading MG prefix and any suffix to get numerical part
    # there may be collisions so suffix 0, 1, etc
    # prefix 2011.50 accession num to make canonical obj id
    if re.match(r'(?i)^mg', outcolvals[objidcolname]):
      outcolvals["Other_Names_and_Numbers/Other_Numbers:Old_Object_ID"] = outcolvals[objidcolname]
      basenum = re.sub(r'(?i)mg\D*|\D.*$','',outcolvals[objidcolname])
      basenum = re.sub(r'^0+','',basenum)
      if "MG"+basenum in objid_base_seen:
        objid_base_seen["MG"+basenum] += 1
      else:
        objid_base_seen["MG"+basenum] = 0
      if objid_base_seen["MG"+basenum] > 10:
        raise Exception("more than 10 like MG"+basenum)
      outcolvals[objidcolname] = "2011.50."+basenum+str(objid_base_seen["MG"+basenum])

    # other oddball object id types to match
    if re.match(r'^(UNKNOWN|\S*#|Paul|MASTER|FF|E-|BB)', outcolvals[objidcolname]):
      if re.search(r'(?i)comedy.shorts',intsv): genre_offset = 0
      elif re.search(r'(?i)features',intsv): genre_offset = 200
      elif re.search(r'(?i)serials',intsv): genre_offset = 400
      elif re.search(r'(?i)animation',intsv): genre_offset = 600
      elif re.search(r'(?i)drama',intsv): genre_offset = 800
      elif re.search(r'(?i)hist.*news',intsv): genre_offset = 1000
      elif re.search(r'(?i)cinema.hist',intsv): genre_offset = 1200
      elif re.search(r'(?i)bartel.*films',intsv): genre_offset = 1400
      elif re.search(r'(?i)test',intsv): genre_offset = 2000
      else: raise Exception("unk obj id and no genre mapping for "+intsv)
      basenum = "2026.67."+str(genre_offset)
      if basenum in objid_base_seen:
        objid_base_seen[basenum] += 1
      else:
        objid_base_seen[basenum] = 0
      outcolvals[objidcolname] = "2026.67."+str(genre_offset+objid_base_seen[basenum])

    # catch remaining noncanonical object id's
    if not re.match(r'^(19|20)\d\d\.\d+\.\d+$',outcolvals[objidcolname]):
      isbadrow += badrow("improper objecty id \""+outcolvals[objidcolname]+f"\" in in line {lnum}: "+ln.strip(),logh)

    # trim object id to create accession number
    outcolvals[accnumcolname] = re.sub(r'\.[^\.]+$','',outcolvals[objidcolname])
    if outcolvals[accnumcolname] == outcolvals[objidcolname]:
      raise Exception("failed to trim obj id for accession id: "+outcolvals[objidcolname])

    # extract film gauge from title: can be like **35mm** or (35mm)
    Aspect_Ratio_title_match = re.match(r'(?i)^(.*?)(?:\*\*|\()(\d+)\s*mm(?:\*\*|\))(.*?)$', outcolvals["Name/Title"])
    if Aspect_Ratio_title_match != None:
      #print("gauge in title: \""+outcolvals["Name/Title"]+"\"")
      coretitle = " ".join((Aspect_Ratio_title_match.group(1) + " " + Aspect_Ratio_title_match.group(3)).split())
      titlefilmgauge = Aspect_Ratio_title_match.group(2) + " mm." # per LOC spec
      #if outcolvals["Aspect_Ratio"] != None and re.search(r'\d+\s*mm', outcolvals["Aspect_Ratio"]) != None and re.search(titlefilmgauge.lower(),outcolvals["Aspect_Ratio"].lower()) == None:
      #  badrow("inconsistent film gauge: title=\""+outcolvals["Name/Title"]+"\" vs aspect ratio=\""+outcolvals["Aspect_Ratio"]+"\"",logh)
      #  continue
      outcolvals["Motion_Picture_Details/Film_Gauge/Format"] = titlefilmgauge
      outcolvals["Name/Title"] = coretitle
      if outcolvals["Aspect_Ratio"] == None:
        outcolvals["Aspect_Ratio"] = "UNKNOWN"
      #print(" now title=\""+outcolvals["Name/Title"]+"\" gauge="+outcolvals["Motion_Picture_Details/Film_Gauge/Format"]+" aspect ratio="+outcolvals["Aspect_Ratio"])
    elif "35mm" in outcolvals["Name/Title"]:
      print("WARNING: gauge REMAINING in title: \""+outcolvals["Name/Title"]+"\"")

    # extract frame rate from aspect ratio, if present
    if outcolvals["Aspect_Ratio"] != None:
      apect_ratio_and_frame_rate_match = re.match(r'(?i)^(.+?)\s+(\d+\s*fps)\s*$', outcolvals["Aspect_Ratio"])
      if apect_ratio_and_frame_rate_match != None:
        outcolvals["Aspect_Ratio"] = apect_ratio_and_frame_rate_match.group(1)
        outcolvals["Motion_Picture_Details/frame_rate"] = apect_ratio_and_frame_rate_match.group(2).upper()

    # extract film gauge from aspect ratio
    if outcolvals["Aspect_Ratio"] != None:
      apect_ratio_and_Film_Gauge_match = re.match(r'^(.+?)\s+(\d+(?:\.\d+)?)\s*mm(\s*.*?)$', outcolvals["Aspect_Ratio"])
      if apect_ratio_and_Film_Gauge_match != None:
        outcolvals["Aspect_Ratio"] = apect_ratio_and_Film_Gauge_match.group(1) + apect_ratio_and_Film_Gauge_match.group(3).strip()
        extracted_gauge = apect_ratio_and_Film_Gauge_match.group(2) + " mm."
        if "Motion_Picture_Details/Film_Gauge/Format" in outcolvals and outcolvals["Motion_Picture_Details/Film_Gauge/Format"] != None and extracted_gauge != outcolvals["Motion_Picture_Details/Film_Gauge/Format"]:
          isbadrow += badrow(f"inconsistent film gauge info in line {lnum}: "+outcolvals["Motion_Picture_Details/Film_Gauge/Format"]+" vs "+extracted_gauge,logh)
        outcolvals["Motion_Picture_Details/Film_Gauge/Format"] = extracted_gauge

    # if film gauge still not filled, that's a problem
    if "Motion_Picture_Details/Film_Gauge/Format" not in outcolvals or outcolvals["Motion_Picture_Details/Film_Gauge/Format"] == None:
      isbadrow += badrow(f"no film gauge found in line {lnum}: "+ln.strip(),logh)

    # film length
    if "Motion_Picture_Details/Length" in outcolvals and outcolvals["Motion_Picture_Details/Length"] != None and len(outcolvals["Motion_Picture_Details/Length"]) > 0:
      # catalogit doesn't want commas in length
      outcolvals["Motion_Picture_Details/Length"] = re.sub(r',','',outcolvals["Motion_Picture_Details/Length"])
      # fix spinal tap stonehenge error
      outcolvals["Motion_Picture_Details/Length"] = re.sub(r'"','\'',outcolvals["Motion_Picture_Details/Length"])
      # if length is not in a valid format, drop it
      if not re.match(r'^\d+(\'|\s*ft)\s*$', outcolvals["Motion_Picture_Details/Length"]):
        print("WARNING: invalid length "+outcolvals["Motion_Picture_Details/Length"]+f" in line {lnum}")
        outcolvals["Motion_Picture_Details/Length"] = None

    # PQ normalization
    if "Condition/Overall_Condition" in outcolvals and outcolvals["Condition/Overall_Condition"] != None and len(outcolvals["Condition/Overall_Condition"].strip()) > 0:
      # if numeric prefix PQ
      if re.match(r'^\s*\d+(\s*[\+\&-]\s*\d*)?\s*$',outcolvals["Condition/Overall_Condition"]):
        outcolvals["Condition/Overall_Condition"] = "PQ" + outcolvals["Condition/Overall_Condition"]
        outcolvals["Condition/Overall_Condition"] = "".join(outcolvals["Condition/Overall_Condition"].split())
      # if n/a, drop
      elif re.match(r'(?i)^\s*n\/a\s*$',outcolvals["Condition/Overall_Condition"]):
        outcolvals["Condition/Overall_Condition"] = None

    # country normalization
    for countryfield in [ "Relationships/Related_Places/Notes:Print_Exhibition_Country", "Made/Created/Place" ]:
      if countryfield in outcolvals and outcolvals[countryfield] != None:
        outcolvals[countryfield] = re.sub(r'^U\W*S\W*A\W*','United States',outcolvals[countryfield])
        outcolvals[countryfield] = re.sub(r'^U\W*S\W*(,|$)',r'United States\1',outcolvals[countryfield])
        outcolvals[countryfield] = re.sub(r'^U\W*K\W*','United Kingdom',outcolvals[countryfield])
        outcolvals[countryfield] = re.sub(r'\bMex\.','Mexico',outcolvals[countryfield])
        outcolvals[countryfield] = " ".join(outcolvals[countryfield].split())
        outcolvals[countryfield] = outcolvals[countryfield].title()

    # actor/director name normalization
    for namefield in [ "Motion_Picture_Details/Cast" ]:
      if namefield in outcolvals and outcolvals[namefield] != None:
        oldval = ",".join(re.split(r'\s*,\s*',outcolvals[namefield]))
        # clobber end-of-string elipses/etc
        outcolvals[namefield] = re.sub(r'\s*,(\W+|\s*etc\.?\s*)$','', outcolvals[namefield])
        # split up some prominent duos
        outcolvals[namefield] = re.sub(r'(?i)\b((laurel|lanuel)\W*\&\W*hardy|l\W*\&\W*h)\b', 'Stan Laurel,Oliver Hardy', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\b(arbuckle\W*\&\W*normand|l\w*\&\w*h)\b', 'Roscoe Arbuckle,Mabel Normand', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\blance\W*\&\W*mabel nicholson\b', 'Lance Nicholson,Mabel Nicholson', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\b(ham\W*\&\W*bud)\b', 'Lloyd Hamilton,Bud Duncan', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bnormand\/sennett\/sterling\b', 'Mabel Normand,Mack Sennett,Ford Sterling', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bnormand\/sennett\b', 'Mabel Normand,Mack Sennett', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bnormand\/ford sterling\b', 'Mabel Normand,Ford Sterling', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bnormand\/charley chase\b', 'Mabel Normand,Charley Chase', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)^arbuckle\/ford sterling\b', 'Roscoe Arbuckle,Ford Sterling', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)^arbuckle\s*\/\s*normand\b', 'Roscoe Arbuckle,Mabel Normand', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)^arbuckle\s*\/\s*keaton\b', 'Roscoe Arbuckle,Buster Keaton', outcolvals[namefield])
        # clean up first names, mostly mapping initials to full names
        outcolvals[namefield] = re.sub(r'(?i)\b(c|charles|chas)\W+chaplin\b', 'Charlie Chaplin', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\b(j)\W+finlayson\b', 'James Finlayson', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\b(e)\W+purviance\b', 'Edna Purviance', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\b(r)\W+arbuckle\b', 'Roscoe Arbuckle', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\b(b)\W+turpin\b', 'Ben Turpin', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bkarr\W*[\&,]\W*alexander\b', 'Hillard Karr,Frank Alexander', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bg\W+(m\W+|broncho\W+billy\W+)*anderson\b','Gilbert M. Anderson', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\be\W+campbell\b','Eric Cambpell', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bgord\W+griffith\b','Gordon Griffith', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bc\W+conklin\b','Chester Conklin', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bm\W+normand\b','Mabel Normand', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bf\W+sterling\b','Ford Sterling', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\b(e\W+|edgar)kennedy\b','Edgar Kennedy', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bm\W+sennett\b','Mack Sennett', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\b(c|charles|chas)\W+chase\b','Charley Chase', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\b(c|charles|chas)\W+parrott\b','Charles Parrott', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bm\W+sennett\b','Mack Sennett', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bm\W+swain\b','Mack Swain', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bs\W+summerville\b','Slim Summerville', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bc\W+bennett\b','Constance Bennett', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bb\W+jamison\b','Bud Jamison', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bb\W+armstrong\b','Billy Armstrong', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bj\W+duffy\b','Jack Duffy', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bb\W+payson\b','Blanche Payson', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bmad\W+hurlock\b','Madeline Hurlock', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)(\blouis\W+|,\W*)fazenda\b','Louise Fazenda', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bo\W+hardy\b','Oliver Hardy', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bt\W+sandford\b','Tiny Sandford', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bb\W+gilbert\b','Billy Gilbert', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bl\W+hamilton\b','Lloyd Hamilton', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bm\W+daniels\b','Mickey Daniels', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bt\W+todd\b','Thelma Todd', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bm\W+busch\b','Mae Busch', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\b(e|eddie|edward)\W+(f\W+)?cline\b','Edward Cline', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bst\W+john\b','St. John', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\btom kendy\b','Tom Kennedy', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bb\W+oldfield\b','Barney Oldfield', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bM.BuschT.Todd\b','Mae Busch,Thelma Todd', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bw\W*c\W+fields\b','W. C. Fields', outcolvals[namefield])
        outcolvals[namefield] = re.sub(r'(?i)\bJackie\s*\/Jack\s+Dailey\b','Jackie Dailey', outcolvals[namefield])
        # if syd chaplin is with charlie, he's often just "syd"
        if re.search(r'(?i)\bchaplin\b',outcolvals[namefield]):
          outcolvals[namefield] = re.sub(r'(?i)(^|,)\s*syd\s*($|,)',r'\1Syd Chaplin', outcolvals[namefield])
        # change ampersand to comma keep mr & mrs (sydney drew); also slash
        if not re.match(r'(?i)^(mr\W*\&\W*mrs)', outcolvals[namefield]):
          outcolvals[namefield] = ",".join(s.strip() for s in re.split(r'[,\&\|\/]',outcolvals[namefield]))
        # check for problematic names 
        for name in outcolvals[namefield].split(","):
          if re.search(r'^\s*\w\W+|^\s*\S+\s*$|\/',name) and re.match(r'^\s*(UNKNOWN|Polidor|Oatmeal|Fatima|Dippy-Doo-Dads|W\. C\. Fields)\s*$',name) == None: # check for names with fn still an initial, and single-word names
            isbadrow += badrow(f"suspect name in line {lnum}: "+name,logh)
        newval = outcolvals[namefield]
        if newval != oldval:
          print(f"NAMEFIX: {oldval} -> {newval}")

    # sound normalization
    if "Motion_Picture_Details/sound/film_sound" in outcolvals and outcolvals["Motion_Picture_Details/Sound/Film_Sound"] != None:
      soundval = outcolvals["Motion_Picture_Details/Sound/Film_Sound"]
      if re.match(r'(?i)^silent$',soundval):
        soundval = "si."
      else:
        outcolvals["Motion_Picture_Details/Sound/Sound_Notes:Type"] = soundval
        soundval = "sd."
      #print(outcolvals["Motion_Picture_Details/Sound/Film_Sound"]+" -> "+soundval+" + "+(outcolvals["Motion_Picture_Details/Sound/Sound_Notes:Type"] if "Motion_Picture_Details/Sound/Sound_Notes:Type" in outcolvals else ""))
      outcolvals["Motion_Picture_Details/Sound/Film_Sound"] = soundval

    # TBD: handle serieses
    # if series col, and filled, prefix to title
    # if "series" in colmap and len(lncols[colmap["series"]].strip()):
    #  lncols[colmap["title"]] = lncols[colmap["series"]].strip() + ": " + lncols[colmap["title"]]

    # aspect gauge normalization; remove word parts, put into a note
    if "Aspect_Ratio" in outcolvals and outcolvals["Aspect_Ratio"] != None:
      Aspect_Ratio_match = re.match(r'^(.*?)([\d\.]+:1)(.*?)$', outcolvals["Aspect_Ratio"])
      if Aspect_Ratio_match == None:
        isbadrow += badrow(f"can't parse aspect ratio in line {lnum}: "+outcolvals["Aspect_Ratio"],logh)
      else:
        outcolvals["Aspect_Ratio"] = Aspect_Ratio_match.group(2)
        ratiolabel = Aspect_Ratio_match.group(1) + " " + Aspect_Ratio_match.group(3)
        if len(ratiolabel.strip()) > 0:
          if re.match(r'(?i)^\s*movietone(\s*ratio)?\s*$',ratiolabel):
            outcolvals["General_Notes:Aperture_Image_Format"] = "Movietone"
          elif re.match(r'(?i)^\s*full\s*silent\s*(aperture|ratio)?\s*$',ratiolabel):
            outcolvals["General_Notes:Aperture_Image_Format"] = "Full Silent"
          elif re.match(r'(?i)^\s*academy\s*(ratio)?\s*$',ratiolabel):
            outcolvals["General_Notes:Aperture_Image_Format"] = "Academy"
          elif re.match(r'(?i)^\s*matted(\s*on\sleft)?\s*$',ratiolabel):
            outcolvals["General_Notes:Aperture_Image_Format"] = "Matted"
          # except! for 8mm, if it's prefixed by super or standard or single, pack it back as prefix of gauge
          elif outcolvals["Motion_Picture_Details/Film_Gauge/Format"] == "8 mm." and re.match(r'(?i)\W*sup(er)?\W*$',ratiolabel):
            outcolvals["Motion_Picture_Details/Film_Gauge/Format"] = "super "+outcolvals["Motion_Picture_Details/Film_Gauge/Format"]
          elif outcolvals["Motion_Picture_Details/Film_Gauge/Format"] == "8 mm." and re.match(r'(?i)\W*(std|standard)?\W*$',ratiolabel):
            outcolvals["Motion_Picture_Details/Film_Gauge/Format"] = "standard "+outcolvals["Motion_Picture_Details/Film_Gauge/Format"]
          # any other random verbiage is an error
          else:
            isbadrow += badrow(f"unexpected aspect ratio label in line {lnum}: "+ratiolabel,logh)

    # extract parenthetical notes from title
    for parenexp in re.findall(r'(\([^\(\)]+\))',outcolvals['Name/Title']):
      if "General_Notes:General" in outcolvals and outcolvals["General_Notes:General"] != None and len(outcolvals["General_Notes:General"].strip()) > 0:
        outcolvals["General_Notes:General"] += "|"+parenexp.strip(" ()")
      else:
        outcolvals["General_Notes:General"] = parenexp.strip().strip(" ()")
    # delte paren exprs from title.  also do whitespace norm
    outcolvals['Name/Title'] = re.sub(r'(\([^\(\)]+\))',' ',outcolvals['Name/Title'])
    outcolvals['Name/Title'] = " ".join(outcolvals['Name/Title'].split())

    # check if cols that were supposed to be supplied by rules actually were
    for colname in colstoberulefilled:
      if colname not in outcolvals or outcolvals[colname] == None:
        isbadrow += badrow(f"no value filled by rule for {colname} (even after rules) in line {lnum}: "+ln.strip(),logh)

    # check for dup objid and dup shelving code
    record_summary = str(lnum)+":"+outcolvals["Name/Title"]+":"+outcolvals["Location/Location"]+":"+outcolvals["Other_Names_and_Numbers/Other_Numbers:Shelving"]
    if outcolvals[objidcolname] in objid_seen:
      isbadrow += badrow("dup objid: "+outcolvals[objidcolname]+": "+objid_seen[outcolvals[objidcolname]]+" VS "+record_summary,logh)
    else:
      objid_seen[outcolvals[objidcolname]] = record_summary
    if outcolvals[objidcolname].lower() in objid_incit:
      isbadrow += badrow("objid already in catalogit: "+outcolvals[objidcolname],logh)
    if "Other_Names_and_Numbers/Other_Numbers:Shelving" in outcolvals:
      normedshelvingcode = re.sub(r'\W','',outcolvals["Other_Names_and_Numbers/Other_Numbers:Shelving"]).lower()
      if normedshelvingcode == "missing":
        pass
      elif normedshelvingcode in shelvingcode_seen:
        print("WARNING: dup shelvingcode: "+normedshelvingcode+": " +shelvingcode_seen[normedshelvingcode]+" VS "+record_summary)
      else:
        shelvingcode_seen[normedshelvingcode] = record_summary

    # normalize location; rack/shelf should be like: r(NUM/UPPERCASELETTERS) sNUM(maybelowercaseletter); no dashes
    if "Location/Location" in outcolvals:
      if re.match(r'(?i)^r\W*\d+\W*s\W*\d',outcolvals["Location/Location"]):
        outcolvals["Location/Location"] = re.sub(
          r'^[rR]\W*([\dA-Z]+)\W*[sS]\W*(\d+)\W*([A-Za-z]*(?:\/[A-Za-z]*)?)',
          lambda m: "r" + m.group(1) + " s" + m.group(2) + m.group(3).lower(),
          outcolvals["Location/Location"])
      elif re.match(r'(?i)^\W*missing\W*$',outcolvals["Location/Location"]):
        outcolvals["Location/Location"] = "MISSING"
      elif re.match(r'(?i)^freezer \w$',outcolvals["Location/Location"]):
        pass
      else:
        isbadrow += badrow(f"misformatted rack/shelf code in {lnum}: "+outcolvals["Location/Location"],logh)

    # for all commasplit cols, replace comma with pipe.
    for colname in outcolvals:
      if outcolvals[colname] != None:
        if colname in commasplitcols:
          outcolvals[colname] = re.sub(r'\s*,\s*','|',outcolvals[colname])

    # cols with colon: strip to basename, store value there, prefix bit after colon
    for coloncol in [colname for colname in outcols if ":" in colname]:
      if coloncol in outcolvals and outcolvals[coloncol] != None and len(outcolvals[coloncol]) > 0:
        beforecolon, aftercolon = coloncol.split(":")
        prefixedval = re.sub(r'_',' ',aftercolon) + ": " + outcolvals[coloncol]
        outcolvals[beforecolon] = outcolvals[beforecolon] + "|" + prefixedval if beforecolon in outcolvals and outcolvals[beforecolon] != None else prefixedval

    # reformat cols with multiple, pipe-delimited values, with json
    # some cols with complicated structures need this even for just one value
    for colname in outcolvals:
      if outcolvals[colname] != None and len(outcolvals[colname]) > 0 and ("|" in outcolvals[colname] or colname in ["General_Notes", "Other_Names_and_Numbers/Other_Numbers"]):
        if colname == "General_Notes":
          vallist = []
          for note in outcolvals[colname].split("|"):
            if ":" in note:
              notetype, notetext = note.split(":",maxsplit=1)
              notetype = " ".join(notetype.strip().split("_"))
              vallist.append({
                "http://www.catalogit.me/rdf/ontologies/core/common#hasNoteType": notetype.strip(),
                "http://www.catalogit.me/rdf/ontologies/core/common#hasNotes": notetext.strip()})
            else:
              vallist.append({"http://www.catalogit.me/rdf/ontologies/core/common#hasNotes": note.strip()})
        elif colname == "Other_Names_and_Numbers/Other_Numbers":
          vallist = []
          for othernum in outcolvals[colname].split("|"):
            numtype, number = othernum.split(":")
            vallist.append({
              "http://www.catalogit.me/rdf/ontologies/core/common#hasType": numtype.strip(),
              "http://www.catalogit.me/rdf/ontologies/core/common#hasValue": number.strip()})
        else:
          vallist = [s.strip() for s in outcolvals[colname].split("|")]
        outcolvals[colname] = json.dumps(vallist)

    # print columns
    novalstr = ""
    outrow = [
      # if undef replace with str indicating empty
      outcolvals[colname] if colname in outcolvals and outcolvals[colname] != None else novalstr
      # for almost all columns
      for colname in
      # skip ones in colon in name because they were mapped into base (before colon) name
      [colname for colname in outcols if ":" not in colname]
    ]
    outrow.append(source)
    outrow.append(str(lnum))
    outh.writerow(outrow)

    # in case badrow()
    if isbadrow > 0:
      print("bad row(s) found!")
      sys.exit(666)
