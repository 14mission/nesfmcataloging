#!/usr/bin/env python
import sys, json

jsfn = sys.argv[1]
fields = sys.argv[2:]


def getfield(obj,field):
    chunks = field.split('.')
    curchunk = chunks[0]
    if curchunk in obj:
        return str(obj[curchunk])
    else:
        return "NONE"

data = None
with open(jsfn, 'r', encoding='utf-8') as file:
    data = json.load(file)

for row in data:
    print("\t".join([getfield(row,f) for f in fields]))
