#!/usr/bin/python

# Copyright (c) 2017, Intel Corporation
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
# OF THE POSSIBILITY OF SUCH DAMAGE.

# convert a CSV or JSON PMU event table to oprofile format
# generic json version
# event-oprofile cpu.csv|cpu.json cpu
from __future__ import print_function
import csv
import sys
import argparse
import json
import copy
import collections
import re

all_names = (
    "all", "all_requests", "any", "all_branches"
)

fixed_counters = {
    "cpu_clk_unhalted.thread": 0x003c,
    "cpu_clk_unhalted.ref_tsc": 0x013c,
    "inst_retired.any": 0x00c0,
}

class Event:
    def __init__(self, code, name, desc):
        self.code = code
        self.name = name
        self.desc = desc
        self.unitmasks = []
        self.minimum = 0
        self.counters = None

class UEvent:
    def __init__(self, umask, name, desc):
        self.name = name
        self.umask = umask
        self.desc = desc
        self.skip = 0
        self.edge = 0
        self.invert = 0
        self.cmask = 0
        self.any = 0
        self.pebs = 0

    def genextra(self):
        extra = "extra:"
        sep = ""
        if self.cmask:
            extra += sep + "cmask=%x" % (self.cmask,)
            sep = ","
        if self.invert:
            extra += sep + "inv"
            sep = ","
        if self.edge:
            extra += sep + "edge"
            sep = ","
        if self.any:
            extra += sep + "any"
            sep = ","
        if self.pebs:
            extra += sep + "pebs"
            sep = ","
        return extra + " "

def row_to_num(x):
    n = 0
    mul = 1
    for i in x[::-1]:
        n += (ord(i) - ord('A') + 1) * mul
        mul *= ord('Z') - ord('A') + 1
    return n -1

def dictopen(fn):
    f = open(fn, 'rb')
    return csv.DictReader(f)

ap = argparse.ArgumentParser()
ap.add_argument('file', help='csv file or json file')
ap.add_argument('cpu', help='Name of CPU')
ap.add_argument('--ignore-pebs2', help='Ignore PEBS=2 for new NPEBS scheme on GLM', action='store_true')
args = ap.parse_args()

cpu = args.cpu
events = {}
unitmasks = {}

if args.file.endswith(".json"):
    r = json.load(open(args.file, "r"))
else:
    r = dictopen(args.file)
for row in r:
    #print(row)
    print(row['EventName'])
    umask = int(row['UMask'].split(",")[0], 16)
    code = int(row['EventCode'].split(",")[0], 16)
    name = row['EventName'].lower().rstrip()
    desc = row['PublicDescription'].rstrip().replace("\n", " ").replace("\r", " ")
    if row['Errata'] != "null":
        desc += " Errata: " + row['Errata']

    counters = row['Counter']
    minimum = row['SampleAfterValue']

    if counters == "":
        print("%s skipped due to empty counter" % (name,))
        continue
    if (counters == "0,1,2,3" and ('CounterHTOff' not in row or row['CounterHTOff'] == '0,1,2,3,4,5,6,7')) or counters.startswith("Fixed "):
        counters = "cpuid"

    # XXX add support to oprofile with perf
    if row['MSRIndex'] != "0":
        print("%s skipped due to extra msr" % (name,))
        continue
    if minimum:
        minimum = int(row['SampleAfterValue'])
    else:
        minimum = 20000

    try:
        (name_base, name_unit) = name.split('.', 1)
    except:
        print(name, "cannot be unpacked")
        continue

    if name in fixed_counters:
        code = fixed_counters[name] & 0xff
        umask = fixed_counters[name] >> 8

    if name_base not in events:
        e = Event(code, name_base, desc)
        events[name_base] = e
    else:
        e = events[name_base]

    name_unit = name_unit.replace(".", "_")
    if re.match(r"[0-9]", name_unit):
        name_unit = "u" + name_unit
    ue = UEvent(umask, name_unit, desc)
    if name_unit in all_names:
        e.unitmasks.insert(0, ue)
    else:
        e.unitmasks.append(ue)

    #if name_unit.endswith("_ps"):
    #   print("setting pebs to",ue.name)
    #   ue.pebs = 1
    #   continue

    ue.cmask = int(row['CounterMask'])
    ue.edge = int(row['EdgeDetect'])
    ue.invert = int(row['Invert'])
    ue.any = int(row['AnyThread'])
    ue.pebs = int(row['PEBS'])
    if args.ignore_pebs2 and ue.pebs == 2:
        ue.pebs = 0

    if minimum > e.minimum:
        e.minimum = minimum

    if e.counters:
        if e.counters != counters:
            print("%s counters do not match %s with %s for %s" % (
                name, counters, e.counters, e.unitmasks[0].name))
            if len(counters) < len(e.counters) and counters != "cpuid":
                e.counters = counters
    else:
        e.counters = counters # XXX HT vs non ht

    if ue.pebs > 0:
        oe = copy.deepcopy(ue)
        ue.pebs = 0
        oe.name = ue.name + "_pebs"
        oe.desc = oe.desc.replace("This is a non-precise version (that is, does not use PEBS) of the event that counts", "Counts")
        e.unitmasks.append(oe)

# remove pebs dups
#for name in events.keys():
#    e = events[name]
#    prev = None
#    for u in sorted(e.unitmasks, key=lambda u: u.umask):
#        if prev != None and prev.umask == u.umask:
#            if prev.desc.count("(Precise Event)") > 0:
#                prev.skip = 1
#            if u.desc.count("(Precise Event)") > 0:
#                u.skip = 1
#        prev = u
#    for u in e.unitmasks[:]:
#        if u.skip:
#            print("Redundant %s for PEBS removed" % (u.name,))
#            e.unitmasks.remove(u)

fe = open(args.cpu + '-events', 'w')
print("""#
# Intel "%s" microarchitecture core events.
#
# See http://ark.intel.com/ for help in identifying %s based CPUs
#
# Note the minimum counts are not discovered experimentally and could be likely
# lowered in many cases without ill effect.
#""" % (cpu, cpu), file=fe)

singleumasks = set()
for name in sorted(events.keys(), cmp=lambda a, b: events[a].code - events[b].code):
    e = events[name]
    um = e.name
    l = len(e.unitmasks)
    if l == 0:
        print("Event %s got eliminated" % (e.name))
        continue
    elif l == 1:
        e.name += "_" + e.unitmasks[0].name
        singleumasks.add((um, e.unitmasks[0]))
        umask = e.unitmasks[0].umask
        del e.unitmasks[0]
        desc = e.desc
    else:
        desc = e.name
    # better than reporting something bogus
    desc = ""
    counters = e.counters

    print("event:0x%02x counters:%s um:%s minimum:%d name:%s :%s%s" % (
        e.code, counters, um, e.minimum, e.name, " " if len(desc) > 0 else "", desc),
          file=fe)

# pick the first umask
def default_umask(ulist):
    masks = [x.umask for x in ulist]
    if max(collections.Counter(masks).values()) > 1:
        return ulist[0].name
    else:
        return "%#2x" % (ulist[0].umask)

fu = open(sys.argv[2] + '-unit_masks', 'w')
print("""#
# Unit masks for the Intel "%s" micro architecture
#
# See http://ark.intel.com/ for help in identifying %s based CPUs
#""" % (cpu, cpu, ), file=fu)

for u in sorted(singleumasks):
    ev = u[0]
    u = u[1]
    umask = u.umask
    print("name:%s type:mandatory default:%#02x" % (
        ev, umask), file=fu)
    print("\t%#02x %s%s %s" % (umask, u.genextra(), u.name, u.desc), file=fu)
for name in sorted(events.keys(), cmp=lambda a, b: events[a].code - events[b].code):
    e = events[name]
    if not e.unitmasks:
        continue
    print("name:%s type:exclusive default:%s" % (
        e.name, default_umask(e.unitmasks)), file=fu)
    for u in e.unitmasks:
        print("\t%#02x %s%s %s" % (u.umask, u.genextra(), u.name, u.desc), file=fu)
