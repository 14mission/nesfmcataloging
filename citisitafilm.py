#!/usr/bin/env python
import sys, re

#how to run this
#export CatalogIt contents as json
#convert to tsv, extracting key fields, and pipe through this script like this
# ./citjson2tsv.py catalogit.export.all_films.2026-06-11.json "Entry/Object ID" "Name/Title" Collection "Motion Picture Details.Film Gauge/Format" "Motion Picture Details.Length" "Made/Created.Notes" "Lexicon.Legacy Lexicon.Object Name" "Location.Location" "Parts.Parts" | ./citisitafilm.py

colmap = None
for ln in sys.stdin:
    cols = ln.split("\t")
    cols[-1] = cols[-1].strip()
    if colmap == None:
        colmap = {}
        cols[0] = re.sub(r'^#','',cols[0])
        for i, col in enumerate(cols):
            colmap[col] = i
        continue
    vals = {}
    for col in colmap:
        vals[col] = cols[colmap[col]].strip()


    # reasons for deciding it's a film
    yeswhy = []
    # valid film gauge
    if re.search(r'\b(8|16|35)\W*m\W*m\b',vals["Motion Picture Details.Film Gauge/Format"]):
        yeswhy.append("gauge:"+vals["Motion Picture Details.Film Gauge/Format"])
    # legacy lex says "Film"
    if re.match(r'(?i)\bfilm$',vals["Lexicon.Legacy Lexicon.Object Name"]):
        yeswhy.append("legacylex:"+vals["Lexicon.Legacy Lexicon.Object Name"])
    # archive location (rack/shelf)
    if re.search(r'(?i)(\br\W*\d+\W*s\W*\d+|SHELF #\d+)',vals["Location.Location"]):
        yeswhy.append("location:"+vals["Location.Location"])
    # parts field with num phys films and lengths
    if re.search(r'(?i)\d+\s*x\s*[\d,]+\s*\'',vals["Parts.Parts"]):
        yeswhy.append("parts:"+vals["Parts.Parts"])
    # length
    if re.match(r'(?i)^[\d,]+\s*(feet|ft\.?|\')$',vals["Motion Picture Details.Length"]):
        yeswhy.append("length:"+vals["Motion Picture Details.Length"])
    # this is specifically to catch header rows for serials that aren't actually individual film listings
    # also some odd 8mm film collections
    if re.search(r'(?i)(16\s*mm.+serials|8\s*mm)',vals["Collection"]):
        yeswhy.append("coll:"+vals["Collection"])

    print(vals["Entry/Object ID"]+"\t"+vals["Name/Title"]+"\t"+("YES:"+", ".join(yeswhy) if len(yeswhy)>0 else "NO:gauge:"+vals["Motion Picture Details.Film Gauge/Format"]+",legacylex:"+vals["Lexicon.Legacy Lexicon.Object Name"]))
