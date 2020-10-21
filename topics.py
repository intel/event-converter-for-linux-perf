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

# generate topics for events
# topics file.json > newfile.json

import json, sys, fnmatch, argparse

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('json')
    ap.add_argument('--show', action='store_true')
    ap.add_argument('--dump', action='store_true')
    args = ap.parse_args()

namemap = (
("ASSISTS.FP", "Floating point"),
("IDQ", "Frontend"),
("RTM", "Memory"),
("HLE", "Memory"),
("*DTLB", "Virtual Memory"),
("*MEMORY_ORDERING", "Memory"),
("CYCLES_ICACHE_MEM_STALLED", "Frontend"),
("UOPS.MS_CYCLES", "Frontend"),
("MACRO_INSTS", "Frontend"),
("MUL", "Pipeline"),
("NO_ALLOC_CYCLES", "Pipeline"),
("CYCLES_DIV_BUSY", "Pipeline"),
("RS_FULL", "Pipeline"),
("DIV", "Pipeline"),
("X87", "Floating point"),
("STORE_FORWARD", "Pipeline"),
("LSD", "Pipeline"),
("BR_", "Pipeline"),
("CPU_CLK", "Pipeline"),
("ITLB", "Virtual Memory"),
("*AVX", "Floating point"),
("ICACHE", "Frontend"),
("*CACHE", "Cache"),
("ILD", "Pipeline"),
("DSB", "Frontend"),
("FRONTEND", "Frontend"),
("BACLEARS", "Frontend"),
("SQ_MISC", "Cache"),
("CORE_REJECT_L2Q", "Cache"),
("UOP_DISPATCHES_CANCELLED", "Pipeline"),
("BOGUS_BR", "Pipeline"),
("TWO_UOP_INSTS_DECODED", "Frontend"),
("MS_DECODED", "Frontend"),
("UOP_UNFUSION", "Pipeline"),
("DL1", "Cache"),
("RECYCLEQ", "Pipeline"),
("INST_", "Pipeline"),
("UOPS_", "Pipeline"),
("INT_MISC", "Pipeline"),
("PARTIAL_RAT_STALLS", "Pipeline"),
("RESOURCE_STALLS", "Pipeline"),
("*_ISSUED", "Pipeline"),
("ROB_MISC_EVENTS", "Pipeline"),
("MACHINE_CLEARS", "Pipeline"),
("OTHER_ASSISTS", "Pipeline"),
("FP_", "Floating point"),
("*_DISPATCHED", "Pipeline"),
("MEM_TRANS_RETIRED", "Memory"),
("MEM_", "Cache"),
("ARITH", "Pipeline"),
("MOVE_ELIMINATION", "Pipeline"),
("TX_MEM", "Memory"),
("TX_EXEC", "Memory"),
("FP_COMP_OPS_EXE", "Floating point"),
("SIMD_FP_256", "Floating point"),
("*_DISPATCHED", "Pipeline"),
("*L3_MISS", "Memory"),
("*LLC_MISS", "Memory"),
("MEM_LOAD_UOPS", "Cache"),
("OFFCORE_RESPONSE*DRAM", "Memory"),
("OFFCORE_RESPONSE*DDR", "Memory"),
("OFFCORE_RESPONSE*MCDRAM", "Memory"),
("OFFCORE_RESPONSE", "Cache"),
("CYCLE_ACTIVITY", "Pipeline"),
("?TLB_", "Virtual Memory"),
("TLB_FLUSH", "Virtual Memory"),
("EPT", "Virtual Memory"),
("PAGE_WALK", "Virtual Memory"),
("STORE", "Cache"),
("SIMD", "Floating point"),
("DATA_TLB", "Virtual Memory"),
("REISSUE", "Pipeline"),
("DECODE", "Frontend"),
("PREFETCH", "Memory"),
("REISSUE", "Pipeline"),
("REHABQ", "Cache"),
("L1D", "Cache"),
("LOAD_HIT_PRE", "Pipeline"),
("LD_BLOCKS", "Pipeline"),
("MISALIGN_MEM_REF", "Memory"),
("AGU_BYPASS_CANCEL", "Pipeline"),
("OFFCORE_REQUESTS", "Cache"),
("L2", "Cache"),
("LONGEST_LAT_CACHE", "Cache"),
("IDQ", "Pipeline"),
("L1D_", "Cache"),
("RESOURCE_STALLS", "Pipeline"),
("INT_MISC", "Pipeline"),
("PARTIAL_RAT_STALLS", "Pipeline"),
("*_RETIRED", "Pipeline"),
("BACLEAR", "Pipeline"),
("EXE_ACTIVITY", "Pipeline"),
("RS_EVENTS", "Pipeline"),
)

def gen_topic(name):
    for pat, top in namemap:
        if fnmatch.fnmatch(name, pat + "*"):
            return top
    return "Other"

if __name__ == '__main__':
    jf = json.load(open(args.json))
    for j in jf:
        name = j["EventName"]
        topic = gen_topic(name)
        if args.show:
            print name, topic
        j["Topic"] = topic

    if args.dump:
        json.dump(jf, sys.stdout, indent=4, separators=(',', ': '))

