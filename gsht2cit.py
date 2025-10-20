#!/usr/bin/env python3
import sys,os,re

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

# columns that should be in output
# note: / can mean either hierarchy field arrangement, or just "aka" in a field name
# also: a colon in and outcol name means CIt field is an array, with label/vals, and the bit after colon is a label
# fields prefixed with * should be manually edited
outcols = [
  "objid","name/title","shelvingcode","location","collection","condition/notes:pq#",
  "motion picture details/production date/date",
  "made/created/notes:Re-Issue Year",
  "*motion picture details/cast",
  "*motion picture details/cast",
  "*motion picture details/director"
]
# if these are not found in input, put UNKNOWN in output.
# for any other column to be empty is an error
okunkcols = ["objid","shelvingcode","location"]
# these are cols that can be empty
okemptycols = ["collection","condition/notes:pq#"]
# these cols can have multiple values

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
        if re.match(r'Acc?ession Num',colstr): colmap["objid"] = colnum
        elif re.match(r'Title',colstr): colmap["name/title"] = colnum
        elif re.match(r'(Shelving|Bartel *-* *Thomsen Film Code)',colstr): colmap["shelvingcode"] = colnum
        elif re.match(r'Film Rack',colstr): colmap["location"] = colnum
        elif re.match(r'(?i)(comedy\s+)?Series',colstr): colmap["collection"] = colnum
        elif re.match(r'(?i)p\s*q\s*#',colstr): colmap["condition/notes:pq#"] = colnum
        elif re.match(r'(?i)prod.*year',colstr): colmap["motion picture details/production date/date"] = colnum
        elif re.match(r'(?i)re\W*issue.*year',colstr): colmap["made/created/notes:Re-Issue Year"] = colnum
        elif re.match(r'(?i)star\W*s\W*',colstr): colmap["*motion picture details/cast"] = colnum
        elif re.match(r'(?i)director',colstr): colmap["*motion picture details/director"] = colnum
      # check that all required output cols were matched
      for field in sorted(colmap.keys()):
        if colmap[field] == None:
          raise Exception("no "+field+" col found in "+intsv+": hdrcols="+",".join(lncols))
        print(field + "=" + str(colmap[field]) + "=" + lncols[colmap[field]], file=logh)
      # check that nothing was mapped unexpectedly
      unexpectedoutputcols = [colname for colname in colmap.keys() if colname not in outcols]
      if len(unexpectedoutputcols) > 0:
        raise Exception("unexpected output column mapping to: "+", ".join(unexpectedoutputcols))
      # check that all input cols were mapped, except ones explicitly known to be unneeded
      unmappedinputcols = [colnum for colnum in range(len(lncols)) if colnum not in colmap.values() and re.search(r'created \d+\/|^\s*$',lncols[colnum]) == None]
      if len(unmappedinputcols) > 0:
        raise Exception("unmapped input cols: "+", ".join(lncols[colnum] for colnum in unmappedinputcols))

      # rest of loop is for regular data lines
      continue

    # section divider line? print it but then ignore
    # other ignorable types too
    if len([col for col in lncols if col != None and len(col.strip())>0]) <= 2 or re.search(r'(?i)(HATS OFF IS A LOST FILM|no prints in archive|NO film prints.+DVD)',ln):
      print(f"skip line: {lnum}: "+ln.strip(), file=logh)
      continue

    # regular line.  make sure all required fields filled
    # some fields can be empty, then we put UNKNOWN
    for colname in outcols:
      if lncols[colmap[colname]] == None or len(lncols[colmap[colname]].strip()) == 0:
        # some cols allowed to be empty
        if colname in okemptycols:
          lncols[colmap[colname]] = None
        # for some cols, we just specify UNKNOWN
        elif colname in okunkcols:
          print(f"empty (use UNKNOWN) {colname} in line {lnum}: "+ln.strip(), file=logh)
          lncols[colmap[colname]] = "UNKNOWN"
        # for others, an empty value is a fatal error
        else:
          print(f"empty (NOTALLOWED) {colname} in line {lnum}:"+ln.strip(), file=logh)
          raise Exception(f"empty (NOTALLOWED) {colname} in line {lnum}:"+ln.strip())

    # TBD: handle serieses
    # if series col, and filled, prefix to title
    # if "series" in colmap and len(lncols[colmap["series"]].strip()):
    #  lncols[colmap["title"]] = lncols[colmap["series"]].strip() + ": " + lncols[colmap["title"]]

    # cols allowed to be empty get explicit "None" for now, may change to empty string later
    print("\t".join(lncols[colmap[colname]] if lncols[colmap[colname]] != None else "None" for colname in outcols)+"\t"+source+"\t"+str(lnum), file=outh)
