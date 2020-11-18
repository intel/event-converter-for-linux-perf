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

# convert json event format to csv
from __future__ import print_function
import sys
import json

headers = "EventCode,UMask,EventName,Description,Counter,OverFlow,MSRIndex,MSRValue,PreciseEvent,Invert,AnyThread,EdgeDetect,CounterMask".split(",")

hdrmap = {
    "Description": "PublicDescription",
    "OverFlow": "SampleAfterValue",
    "PreciseEvent": "PEBS",
}

alt = {
    "PublicDescription": "BriefDescription",
}

def translate(j, x):
    if x in j:
        return j[x]
    v = j[hdrmap[x]]
    if v == "null":
        v = j[alt[hdrmap[x]]]
    return v

def oline(j):
    return ('"' +
            u'","'.join(map(lambda x: translate(j, x).replace('"', ''), headers)).encode('utf-8') +
            '"')

header = False
for fn in sys.argv[1:]:
    f = open(fn, "r")
    jo = json.load(f)
    for j in jo:
        if not header:
            print(",".join(headers))
            header = True
        print(j['EventName'], file=sys.stderr)
        if j['PublicDescription'].find("This is a non-precise version") >= 0:
            j['PublicDescription'] = 'null'
        if j['PublicDescription'].find("This is a precise version") < 0:
            print(oline(j))
        if j['PEBS'] == "1":
            j['EventName'] += "_PS"
            j['BriefDescription'] += " (Uses PEBS)"
            print(oline(j))
