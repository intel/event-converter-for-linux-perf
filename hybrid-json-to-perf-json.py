#!/usr/bin/python
# generate hybrid perf json files from two perf json files (core and atom)
# For example,
#   hybrid-json-to-perf-json.py alderlake_gracemont_core_v0.01_private.json alderlake_goldencove_v0.01_private.json
import os
import re
import json
import argparse
import sys
import importlib
json_to_perf_json = importlib.import_module("json-to-perf-json")

ap = argparse.ArgumentParser()
ap.add_argument('atomjson', type=argparse.FileType('r'), help="Input atom json file")
ap.add_argument('corejson', type=argparse.FileType('r'), help="Input core json file")
ap.add_argument('--outdir', default='.')
args = ap.parse_args()

os.system('rm -rf tmp-atom tmp-core')
os.system('mkdir -p tmp-atom')
os.system('mkdir -p tmp-core')

atom_out = json_to_perf_json.json_to_perf_json(args.atomjson, "tmp-atom", "cpu_atom")
core_out = json_to_perf_json.json_to_perf_json(args.corejson, "tmp-core", "cpu_core")

inter = list(set(atom_out).intersection(set(core_out)))
diff1 = list(set(core_out).difference(set(atom_out)))
diff2 = list(set(atom_out).difference(set(core_out)))

def combine_jsons(atom_path, core_path, name, out_path):
    jn = []

    if len(atom_path) > 0:
        f = open(atom_path, 'r')
        ja = json.load(f)
        if isinstance(ja, dict) and ja["Header"]:
            ja = ja["Events"]
        for l in ja:
            jn.append(l)
        f.close()

    if len(core_path) > 0:
        f = open(core_path, 'r')
        jc = json.load(f)
        if isinstance(jc, dict) and jc["Header"]:
            jc = jc["Events"]
        for l in jc:
            jn.append(l)
        f.close()

    ofile = open("%s/%s" % (out_path, name), "w")
    json.dump(jn, ofile, sort_keys=True, indent=4, separators=(',', ': '))
    ofile.write("\n")
    ofile.close()

for s in inter:
    atom_path = "./tmp-atom/" + s
    core_path = "./tmp-core/" + s
    combine_jsons(atom_path, core_path, s, args.outdir)

for s in diff1:
    core_path = "./tmp-core/" + s
    combine_jsons('', core_path, s, args.outdir)

for s in diff2:
    atom_path = "./tmp-core/" + s
    combine_jsons(atom_path, '', s, args.outdir)
