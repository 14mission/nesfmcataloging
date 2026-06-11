#!/usr/bin/env python
import sys, json

jsfn = sys.argv[1]
fields = sys.argv[2:]


def getfield(obj,field):
    chunks = field.split('.')
    if len(chunks) > 1:
        raise Exception(f"hierarchical fields like {field} not supported yet")
    curchunk = chunks[0]
    if curchunk not in obj:
        return "NONE"
    if isinstance(obj[curchunk], list):
        return "|".join(str(item) for item in obj[curchunk])
    else:
        return str(obj[curchunk])

data = None
with open(jsfn, 'r', encoding='utf-8') as file:
    data = json.load(file)

print("#"+"\t".join(fields))
for row in data:
    print("\t".join([getfield(row,f) for f in fields]))
