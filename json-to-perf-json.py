#!/usr/bin/python3

# Copyright (c) 2020, Intel Corporation
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#  * Neither the name of Intel Corporation nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

# generate split perf json files from a single perf json files
# mapfile still needs to be updated separately
from __future__ import print_function
import os
import itertools
import json
import argparse
import sys
import perfjson

sys.path.append(os.path.dirname(sys.argv[0]))

ap = argparse.ArgumentParser()
ap.add_argument('jsonfile', type=argparse.FileType('r'), help="Input json file")
ap.add_argument('--outdir', default='.')
ap.add_argument('--unit', default='')
args = ap.parse_args()

oname = perfjson.gen_oname(args.jsonfile.name).replace(".json", "").split("_")[0]
jf = json.load(args.jsonfile)
if isinstance(jf, dict) and jf["Header"]:
    jf = jf["Events"]
perfjson.cleanjf(jf)
jf = perfjson.del_dup_events(jf)
jf = map(perfjson.fix_names, jf)
jf = perfjson.del_special_events(jf)

if args.unit:
    jf = perfjson.add_unit(jf, args.unit)

jf = sorted(jf, key=lambda x: x["Topic"])

for topic, nit in itertools.groupby(jf, lambda x: x["Topic"]):
    def del_topic(n):
        del n["Topic"]
        return n
    def do_strip(n):
        for k in n.keys():
            if n[k] is None:
                del n[k]
                continue
            n[k] = n[k].strip()
            if n[k] == "0x00":
                del n[k]
        return n

    j2 = list(nit)
    j2 = map(del_topic, j2)
    j2 = map(do_strip, j2)
    if not j2:
        continue
    topic = topic.replace(" ", "-")
    fn = topic.lower() + ".json"
    print(fn)
    ofile = open("%s/%s" % (args.outdir, fn), "w")
    json.dump(sorted(list(j2), key=lambda x: x["EventName"]), ofile,
              sort_keys=True, indent=4, separators=(',', ': '))
    ofile.write("\n")
    ofile.close()
