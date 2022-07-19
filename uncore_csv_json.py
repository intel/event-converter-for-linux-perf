#!/usr/bin/python

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

# generate split uncore json from csv spreadsheet input
# uncore_csv_json.py csv orig-pme-json targetdir
import json
import sys
import csv
import copy
import argparse
import itertools
import re
from typing import TextIO

repl_events = {
    "UNC_M_CLOCKTICKS": "UNC_M_DCLOCKTICKS"
}


def read_events(file: TextIO):
    events = {}
    j = json.load(file)
    if isinstance(j, dict) and j["Header"]:
        j = j["Events"]
    for l in j:
        events[l["EventName"]] = l
    return events

def gen_topic(u):
    if u == "iMC":
        return "Uncore-Memory"
    if u == "CBO" or u == "HA":
        return "Uncore-Cache"
    if u.startswith("QPI"):
        return "Uncore-Interconnect"
    if u == "PCU":
        return "Uncore-Power"
    return "Uncore-Other"

def update(j):
    if j["Unit"] == "PCU" and "UMask" in j:
	# XXX should convert to right filter for occupancy
        del j["UMask"]
    unit_remap = {
	"IMC": "iMC",
	"KTI LL": "UPI",
    }
    if j["Unit"] in unit_remap:
        j["Unit"] = unit_remap[j["Unit"]]
    if j["Unit"] == "NCU" and j["EventName"] == "UNC_CLOCK.SOCKET":
        j["Unit"] = "CLOCK"
    j["Topic"] = gen_topic(j["Unit"])
    j["PerPkg"] = "1"
    if "Counter" in j and j["Counter"] in ("FIXED","Fixed"):
        j["EventCode"] = "0xff"
        j["UMask"] = "0x00"
    for k in list(j.keys()):
        if j[k] in ("0x0", "0x00", "0X00", "null", "", "0", None, "tbd", "TBD", "na"):
            del j[k]
    return j

def uncore_csv_json(csvfile: TextIO, jsonfile: TextIO, extrajsonfile: TextIO, targetdir: str, all_events: bool, verbose: bool):
    verboseprint = print if verbose else lambda *a, **k: None
    events = read_events(jsonfile)
    events2 = read_events(extrajsonfile) if extrajsonfile else None

    jl = []
    added = set()
    c = csv.reader(csvfile)
    for l in c:
        # UNC_C_LLC_LOOKUP.ANY,new name,All LLC Misses (code+ data rd + data wr - including demand and prefetch),"State=0x1,",scale,formula (with x),comment (optional)
        if len(l) == 6:
            l.append("")
        name, newname, desc, filter, scale, formula, comment = l
        umask = None
        if ":" in name:
            name, umask = name.split(":")
            umask = umask[1:]

        if filter:
            filter = filter.replace("State=", ",filter_state=")
            filter = filter.replace("Match=", ",filter_opc=")
            filter = filter.replace(":opc=", ",filter_opc=")
            filter = filter.replace(":nc=", ",filter_nc=")
            filter = filter.replace(":tid=", ",filter_tid=")
            filter = filter.replace(":state=", ",filter_state=")
            filter = filter.replace(":filter1=", ",config1=")
            filter = filter.replace("fc, chnl", "")
            m = re.match(r':u[0-9xa-f]+', filter)
            if m:
                umask = "%#x" % int(m.group(0)[2:], 16)
                filter = filter.replace(m.group(0), '')
            if filter and filter[0] == ",":
                filter = filter[1:]
            if filter.endswith(","):
                filter = filter[:-1]

        def find_event(events, name):
            if name in events:
                return events[name]
            if name in repl_events:
                name = repl_events[name]
                if name in events:
                    return events[name]
            nname = name[:name.rfind(".")]
            if nname in events:
                j = events[nname]
            return None

        def find_event_all(name):
            j = find_event(events, name)
            if j:
                return j
            if events2:
                return find_event(events2, name)
            return None

        j = find_event_all(name)

        def is_deprecated(j):
            return "Deprecated" in j and j["Deprecated"] == "1"

        if j is None or is_deprecated(j):
            for i, r in (("_H_", "_CHA_"), ("_C_", "_CHA_")):
                nname = name.replace(i, r)
                j = find_event_all(nname)
                if j:
                    name = nname
                    break

        if j is None:
            print("event", name, "not found", file=sys.stderr)
            continue

        if is_deprecated(j):
            print("Could not find non deprecated version of", name, file=sys.stderr)

        j = update(j)

        j["EventName"] = newname if newname else name
        if desc == "" and "BriefDescription" in j:
            desc = j["BriefDescription"]
        if "Description" in j:
            del j["Description"]
        if desc.endswith("."):
            desc = desc[:-1]
        j["BriefDescription"] = desc
        if newname and newname.lower() != name.lower():
            BriefDescription1 = j["BriefDescription"]
            j["BriefDescription"] += ". Derived from " + name.lower()
        if "PublicDescription" in j:
            del j["PublicDescription"]
        j["Filter"] = filter
        if formula:
            # XXX hack for now
            nn = newname if newname else name
            formula = re.sub(r"X/", nn+ "/", formula)
            for o in repl_events.keys():
                if o in formula and o not in events:
                    formula = formula.replace(o, repl_events[o])
            # Don't apply % for Latency Metrics
            if "/" in formula and "LATENCY" not in nn:
                j["MetricExpr"] = "(%s) * 100." % (formula.replace("/", " / "))
                j["MetricName"] = re.sub(r'UNC_[A-Z]_', '', nn).lower() + " %"
            else:
                j["MetricExpr"] = formula.replace("\n", "")
                j["MetricName"] = nn
        if umask:
            j["UMask"] = "%#02x" % int(umask, 16)
        if scale:
            # If scale has a unit, use it
            if "(" in scale:
                scale = scale.replace("(", "")
                j["ScaleUnit"] = scale.replace(")", "")
            else:
                j["ScaleUnit"] = scale + "Bytes"
        if j["EventName"] in added:
            print(j["EventName"], "duplicated", file=sys.stderr)
            continue
        j = update(j)
        added.add(j["EventName"])
        if newname and newname.lower() != name.lower():
            added.add(name)
        jl.append(copy.deepcopy(j))
        if newname:
            j["EventName"] = name
            j["BriefDescription"] = BriefDescription1
            jl.append(copy.deepcopy(j))
            verboseprint("Both event", name, "and its new name", newname, "are supported", file=sys.stderr)

    if all_events:
        jl += [update(events[x]) for x in sorted(events.keys()) if x not in added]

    for j in jl:
        if "UMask" in j.keys() and "UMaskExt" in j.keys():
            str = j["UMask"][2:]
            j["UMask"] = j["UMaskExt"] + str
        if "FILTER_VALUE" in j.keys() and j["Filter"] == "Filter1":
            j["Filter"] = "config1=" + j["FILTER_VALUE"]
            del j["FILTER_VALUE"]

        desc = None
        if "BriefDescription" in j:
            desc = j["BriefDescription"]
        if "PublicDescription" in j:
            desc = j["PublicDescription"]
        if not desc:
            verboseprint(j["EventName"], "has no description", file=sys.stderr)
        if desc and len(desc) > 900:
            verboseprint(j["EventName"], "has too long description for git (%d)" % len(desc), file=sys.stderr)

    #print(jl)
    remove_l = []
    for j in jl:
        if "Filter" in j.keys():
            if j["Filter"].startswith('CHAFilter'):
                remove_l.append(j)
            if j["Filter"] == "fc, chnl" or j["Filter"].startswith('chnl'):
                del j["Filter"]
        if "BriefDescription" not in j.keys() and "PublicDescription" not in j.keys():
            remove_l.append(j)

    for j in remove_l:
        jl.remove(j)

    def get_topic(j):
        return j["Topic"]

    for topic, iter in itertools.groupby(sorted(jl, key=get_topic), key=get_topic):
        events = list(iter)
        for j in events:
            del j["Topic"]
        verboseprint("generating", topic)
        of = open(targetdir + "/" + topic.lower() + ".json", "w", encoding='ascii')
        js = json.dumps(events, sort_keys=True, indent=4, separators=(',', ': '))
        print(js, file=of)
        of.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csvfile', type=argparse.FileType('r'), help='CSV file that lists uncore events and fixes')
    ap.add_argument('jsonfile', type=argparse.FileType('r'), help='Uncore event json file')
    ap.add_argument('targetdir', help='Output directory')
    ap.add_argument('extrajsonfile', nargs='?', type=argparse.FileType('r'), help='Extra json file to look up events (e.g. experimential)')
    ap.add_argument('--all', action='store_true', help='Include all events from jsonfile, not just CSV events')
    ap.add_argument('--verbose', action='store_true')
    args = ap.parse_args()

    uncore_csv_json(args.csvfile, args.jsonfile, args.extrajsonfile, args.targetdir, args.all, args.verbose)

if __name__ == '__main__':
    main()
