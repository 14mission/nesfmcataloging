#!/usr/bin/env python
import sys, json, re

jsfn = sys.argv[1]
fields = sys.argv[2:]

def escnltab(s):
    s = re.sub(r'\n',r'\\n',s)
    s = re.sub(r'\t',r'\\t',s)
    return s

def getfield(obj,field):
    chunks = field.split('.')
    curchunk = chunks[0]
    if curchunk not in obj:
        return "NONE"
    elif len(chunks) > 1:
        return getfield(obj[curchunk], ".".join(chunks[1:]))
    elif isinstance(obj[curchunk], list):
        return "|".join(escnltab(str(item)) for item in obj[curchunk])
    elif len(str(obj[curchunk]).strip()) == 0:
        return "EMPTY"
    else:
        return escnltab(str(obj[curchunk]))

data = None
with open(jsfn, 'r', encoding='utf-8') as file:
    data = json.load(file)

print("#"+"\t".join(fields))
for row in data:
    print("\t".join([getfield(row,f) for f in fields]))
