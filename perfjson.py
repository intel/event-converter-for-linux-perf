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

# shared code for perf json generation

import os
import re
import itertools
import json
import argparse
import sys
sys.path.append(os.path.dirname(sys.argv[0]))
import topics

def gen_oname(path):
    oname = os.path.basename(path)
    oname = re.sub(r'_V\d+', '', oname)
    return oname

def cleanjf(jf):
    for ind in range(len(jf) -1, -1, -1):
        if jf[ind]["EventName"].startswith("OFFCORE_RESPONSE_1"):
            del jf[ind]
        if jf[ind]["EventName"].startswith("OFFCORE_RESPONSE_0"):
            jf[ind]["EventName"] = jf[ind]["EventName"].replace("OFFCORE_RESPONSE_0", "OFFCORE_RESPONSE")
        for k, v in jf[ind].items():
            jf[ind][k] = ''.join([c if ord(c) < 128 else '' for c in v])

def fix_names(j):
    if "Description" in j and "BriefDescription" not in j:
        j["BriefDescription"] = j["Description"]
    if "Internal" in j and j["Internal"] == "1":
        j["EventCode"] = "%#x" % (int(j["EventCode"], 16) | (1 << 21))
    if "BriefDescription" in j and "PublicDescription" in j and j["BriefDescription"] == j["PublicDescription"]:
        del j["PublicDescription"]
    if "BriefDescription" in j and "TBD" in j["BriefDescription"]:
        if j["EventName"].startswith('OCR.'):
            str = j["EventName"].replace('OCR.', '').replace('.', ' & ')
            j["BriefDescription"] = j["BriefDescription"].replace('TBD', str, 1).replace('TBD', '')
    j["Topic"] = topics.gen_topic(j["EventName"])
    #if j["Topic"] == "Other" and typ == "uncore":
    #    del j["Topic"]
    if "Internal" in j:
        j["ExtSel"] = j["Internal"]
        del j["Internal"]
    if j["EventName"].startswith("OFFCORE_RESPONSE") and j["BriefDescription"] == "tbd":
        j["BriefDescription"] = j["EventName"].replace("OFFCORE_RESPONSE.", "").replace(".", " & ")
    for k in list(j.keys()):
        if j[k] == 0 or j[k] == "0" or j[k] == "null" or j[k] == "tbd" or j[k] == "0x00" or j[k] == "":
            del j[k]
    if "UMask" in j:
        if j["UMask"].startswith("fixed ctr"):
            v = int(j["UMask"].split("fixed ctr")[1]) + 1
            j["UMask"] = "%#x" % v
        else:
            j["UMask"] = "%#x" % int(j["UMask"].split(",")[0], 16)

    if j["EventName"].startswith("OFFCORE_RESPONSE:request="):
        str = j["EventName"]
        m = re.match(r'OFFCORE_RESPONSE:request=(.*):response=(.*)', str)
        if m:
            j["EventName"] = "OFFCORE_RESPONSE." + m.group(1) + "." + m.group(2)
    return j

def del_topic(n):
    del n["Topic"]
    return n

def del_dup_events(jf):
    events = {}
    for i in range(len(jf)):
        name = jf[i]["EventName"]
        if name not in events.keys():
            events[name] = jf[i]
        else:
            if "BriefDescription" in events[name] and "TBD" in events[name]["BriefDescription"]:
                if "TBD" not in jf[i]["BriefDescription"]:
                    events[name] = jf[i]
    jf = events.values()
    return jf

def del_special_events(jf):
    del_l = []
    jf_l = list(jf)
    for i in range(len(jf_l)):
        if jf_l[i]["EventName"].startswith("CORE_SNOOP") and "BriefDescription" not in jf_l[i]:
            del_l.append(jf_l[i])
    for j in del_l:
        jf_l.remove(j)
    return jf_l

def add_unit(jf, unit):
    for i in range(len(jf)):
        jf[i]["Unit"] = unit
    return jf
