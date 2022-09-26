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

# extract metrics for cpu from TMA spreadsheet and generate JSON metrics files
# extract-tma-metrics.py CPU tma-csv-file.csv > cpu-metrics.json
import csv
import argparse
import re
import json
import sys
from typing import (Sequence, TextIO)

# metrics redundant with perf or unusable
ignore = set(['MUX', 'Power', 'Time'])

groups = {
    'IFetch_Line_Utilization': 'Frontend',
    'Kernel_Utilization': 'Summary',
    'Turbo_Utilization': 'Power',
}

spr_event_fixes = (
    ('UNC_CHA_CLOCKTICKS:one_unit', r'uncore_cha_0@event=0x1@'),
    ('UNC_M_CLOCKTICKS:one_unit', 'uncore_imc_0@event=0x1,umask=0x1@'),
    ('UNC_CHA_TOR_OCCUPANCY.IA_MISS_DRD:c1',
     r'cha@UNC_CHA_TOR_OCCUPANCY.IA_MISS_DRD,thresh=1@'),
    ('UNC_M_CAS_COUNT.RD', 'uncore_imc@cas_count_read@'),
    ('UNC_M_CAS_COUNT.WR', 'uncore_imc@cas_count_write@'),
)

icx_event_fixes = (
    ('UNC_CHA_CLOCKTICKS:one_unit', r'cha_0@event=0x0@'),
    ('UNC_M_CLOCKTICKS:one_unit', 'imc_0@event=0x0@'),
    ('UNC_CHA_TOR_OCCUPANCY.IA_MISS_DRD:c1',
     r'cha@event=0x36,umask=0xC817FE01,thresh=1@'),
    ('UNC_M_CAS_COUNT.RD', 'uncore_imc@cas_count_read@'),
    ('UNC_M_CAS_COUNT.WR', 'uncore_imc@cas_count_write@'),
    ('UNC_M_PMM_RPQ_INSERTS', 'imc@event=0xe3@'),
    ('UNC_M_PMM_WPQ_INSERTS', 'imc@event=0xe7@'),
    ('UOPS_RETIRED.RETIRE_SLOTS', 'UOPS_RETIRED.SLOTS'),
)

# XXX replace with ocperf
event_fixes = (
    ('L1D_PEND_MISS.PENDING_CYCLES,amt1',
     'cpu@l1d_pend_miss.pending_cycles\\,any=1@'),
    ('MEM_LOAD_UOPS_RETIRED.HIT_LFB_PS', 'mem_load_uops_retired.hit_lfb'),
    # uncore hard coded for now for SKX.
    # FIXME for ICX if events are changing
    #SKX:
    ('UNC_M_CAS_COUNT.RD', 'uncore_imc@cas_count_read@'),
    ('UNC_M_CAS_COUNT.WR', 'uncore_imc@cas_count_write@'),
    ('UNC_CHA_TOR_OCCUPANCY.IA_MISS_DRD:c1',
     r'cha@event=0x36,umask=0x21,config=0x40433,thresh=1@'),
    ('UNC_CHA_TOR_OCCUPANCY.IA_MISS_DRD',
     r'cha@event=0x36,umask=0x21,config=0x40433@'),
    ('UNC_CHA_CLOCKTICKS:one_unit', r'cha_0@event=0x0@'),
    ('UNC_CHA_TOR_INSERTS.IA_MISS_DRD',
     r'cha@event=0x35,umask=0x21,config=0x40433@'),
    ('UNC_M_PMM_RPQ_OCCUPANCY.ALL', r'imc@event=0xe0,umask=0x1@'),
    ('UNC_M_PMM_RPQ_INSERTS', 'imc@event=0xe3@'),
    ('UNC_M_PMM_WPQ_INSERTS', 'imc@event=0xe7@'),
    ('UNC_M_CLOCKTICKS:one_unit', 'imc_0@event=0x0@'),
    # SKL:
    ('UNC_ARB_TRK_OCCUPANCY.DATA_READ:c1', 'arb@event=0x80,umask=0x2,cmask=1@'),
    ('UNC_ARB_TRK_OCCUPANCY.DATA_READ', 'arb@event=0x80,umask=0x2@'),
    ('UNC_ARB_TRK_REQUESTS.ALL', 'arb@event=0x81,umask=0x1@'),
    ('UNC_ARB_COH_TRK_REQUESTS.ALL', 'arb@event=0x84,umask=0x1@'),
    # BDX
    ('UNC_C_TOR_OCCUPANCY.MISS_OPCODE:opc=0x182:c1',
     'cbox@event=0x36,umask=0x3,filter_opc=0x182,thresh=1@'),
    ('UNC_C_TOR_OCCUPANCY.MISS_OPCODE:opc=0x182',
     'cbox@event=0x36,umask=0x3,filter_opc=0x182@'),
    ('UNC_C_TOR_INSERTS.MISS_OPCODE:opc=0x182:c1',
     'cbox@event=0x35,umask=0x3,filter_opc=0x182,thresh=1@'),
    ('UNC_C_TOR_INSERTS.MISS_OPCODE:opc=0x182',
     'cbox@event=0x35,umask=0x3,filter_opc=0x182@'),
    ('UNC_C_CLOCKTICKS:one_unit', 'cbox_0@event=0x0@'),
)

# copied from toplev parser. unify?
ratio_column = {
    "IVT": ("IVT", "IVB", "JKT/SNB-EP", "SNB"),
    "IVB": ("IVB", "SNB", ),
    "HSW": ("HSW", "IVB", "SNB", ),
    "HSX": ("HSX", "HSW", "IVT", "IVB", "JKT/SNB-EP", "SNB"),
    "BDW": ("BDW", "HSW", "IVB", "SNB", ),
    "BDX": ("BDX", "BDW", "HSX", "HSW", "IVT", "IVB", "JKT/SNB-EP", "SNB"),
    "SNB": ("SNB", ),
    "JKT/SNB-EP": ("JKT/SNB-EP", "SNB"),
    "SKL/KBL": ("SKL/KBL", "BDW", "HSW", "IVB", "SNB"),
    'SKX': ('SKX', 'SKL/KBL', 'BDX', 'BDW', 'HSX', 'HSW', 'IVT', 'IVB',
            'JKT/SNB-EP', 'SNB'),
    "KBLR/CFL": ("KBLR/CFL", "SKL/KBL", "BDW", "HSW", "IVB", "SNB"),
    'CLX': ('CLX', 'KBLR/CFL/CML', 'SKX', 'SKL/KBL', 'BDX', 'BDW', 'HSX', 'HSW',
            'IVT', 'IVB', 'JKT/SNB-EP', 'SNB'),
    "ICL": ("ICL", "CNL", "KBLR/CFL/CML", "SKL/KBL", "BDW", "HSW", "IVB", "SNB"),
    'ICX': ('ICX', 'ICL', 'CNL', 'CPX', 'CLX', 'KBLR/CFL/CML', 'SKX', 'SKL/KBL',
            'BDX', 'BDW', 'HSX', 'HSW', 'IVT', 'IVB', 'JKT/SNB-EP', 'SNB'),
    'RKL': ('RKL', 'ICL', 'CNL', 'KBLR/CFL/CML', 'SKL/KBL', 'BDW', 'HSW',
            'IVB', 'SNB'),
    'TGL': ('TGL', 'RKL', 'ICL', 'CNL', 'KBLR/CFL/CML', 'SKL/KBL', 'BDW',
            'HSW', 'IVB', 'SNB'),
    'ADL/RPL': ('ADL/RPL', 'TGL', 'RKL', 'ICL', 'CNL', 'KBLR/CFL/CML',
                'SKL/KBL', 'BDW', 'HSW', 'IVB', 'SNB'),
    'SPR': ('SPR', 'ADL/RPL', 'TGL', 'RKL', 'ICX', 'ICL', 'CNL', 'CPX', 'CLX',
            'KBLR/CFL/CML', 'SKX', 'SKL/KBL', 'BDX', 'BDW', 'HSX', 'HSW', 'IVT',
            'IVB', 'JKT/SNB-EP', 'SNB'),
    "GRT": ("GRT"),
}

cstates = [
    (['NHM', 'WSM'], [3, 6], [3, 6, 7]),
    ([  'SNB', 'IVB', 'HSW', 'BDW', 'BDX', 'SKL', 'SKX', 'CLX', 'CPX', 'HSX',
        'IVT', 'JKT'
    ], [3, 6, 7], [2, 3, 6, 7]),
    (['KBL'], [3, 6, 7], [2, 3, 6, 7]),
    (['CNL'], [1, 3, 6, 7], [2, 3, 6, 7, 8, 9, 10]),
    (['ICL', 'TGL', 'RKL'], [6, 7], [2, 3, 6, 7, 8, 9, 10]),
    (['ICX', 'SPR'], [1, 6], [2, 6]),
    (['ADL', 'GRT'], [1, 6, 7], [2, 3, 6, 7, 8, 9, 10]),
    (['SLM'], [1, 6], [6]),
    (['KNL', 'KNM'], [6], [2, 3, 6]),
    (['GLM', 'SNR'], [1, 3, 6], [2, 3, 6, 10]),
]

def find_tma_cpu(shortname):
    if shortname == 'BDW-DE':
        return 'BDX'
    for key in ratio_column.keys():
        if shortname in key:
            return key
    return None

def check_expr(expr):
    if expr.count('(') != expr.count(')'):
        raise Exception('Mismatched parentheses', expr)
    return expr


def bracket(expr):
    expr = check_expr(expr)
    if '/' in expr or '*' in expr or '+' in expr or '-' in expr:
        if expr.startswith('(') and expr.endswith(')'):
            return expr
        else:
            return '(' + expr + ')'
    return expr


def update_fix(x):
    x = x.replace(',', r'\,')
    x = x.replace('=', r'\=')
    return x


class BadRef(Exception):

    def __init__(self, v):
        self.name = v


def badevent(e):
    if 'UNC_CLOCK.SOCKET' in e.upper():
        raise BadRef('UNC_CLOCK.SOCKET')
    if 'BASE_FREQUENCY' in e.upper():
        raise BadRef('Base_Frequency')
    if '/Match=' in e:
        raise BadRef('/Match=')


def add_sentence(s, n):
    s = s.strip()
    if not s.endswith('.'):
        s += '.'
    return s + ' ' + n


def count_metric_events(v):
    global counts
    counts = counts + 1


def find_cstates(cpu):
    for (cpu_matches, core_cstates, pkg_cstates) in cstates:
        for x in cpu_matches:
            if cpu.startswith(x):
                return (core_cstates, pkg_cstates)
    raise Exception('Unknown cstates for CPU ' + cpu)


def cstate_json(cpu):
    (core_cstates, pkg_cstates) = find_cstates(cpu)
    result = []
    for x in core_cstates:
        result.append({
            'MetricExpr':
                '(cstate_core@c{}\\-residency@ / msr@tsc@) * 100'.format(x),
            'MetricGroup':
                'Power',
            'BriefDescription':
                'C{} residency percent per core'.format(x),
            'MetricName':
                'C{}_Core_Residency'.format(x)
        })
    for x in pkg_cstates:
        result.append({
            'MetricExpr':
                '(cstate_pkg@c{}\\-residency@ / msr@tsc@) * 100'.format(x),
            'MetricGroup':
                'Power',
            'BriefDescription':
                'C{} residency percent per package'.format(x),
            'MetricName':
                'C{}_Pkg_Residency'.format(x)
        })
    return result


def extract_tma_metrics(csvfile: TextIO, cpu: str, extrajson: TextIO,
                        cstate: bool, extramodel: str, unit: str,
                        expr_events: str, memory: bool, verbose: bool,
                        outfile: TextIO):
    verboseprint = print if verbose else lambda *a, **k: None
    csvf = csv.reader(csvfile)

    class PerfMetric:
       def  __init__(self, name: str, form: str, desc: str, groups: str, locate: str):
           self.name = name
           self.form = form
           self.desc = desc
           self.groups = groups
           self.locate = locate

    # All the metrics read from the CSV file.
    info : Sequence[PerfMetric] = []
    aux = {}
    infoname = {}
    nodes = {}
    l1nodes = []
    resolved = []
    counts = 0
    for l in csvf:
        if l[0] == 'Key':
            f = {name: ind for name, ind in zip(l, range(len(l)))}
            #print(f)
        def field(x):
            return l[f[x]]

        def find_form():
            if field(cpu):
                return check_expr(field(cpu))
            for j in ratio_column[cpu]:
                if field(j):
                    return check_expr(field(j))
            return None

        if l[0].startswith('BE') or l[0].startswith('BAD') or l[0].startswith(
                'RET') or l[0].startswith('FE'):
            for j in ('Level1', 'Level2', 'Level3', 'Level4'):
                if field(j):
                    form = find_form()
                    nodes[field(j)] = form
                    if j == 'Level1':
                        info.append(PerfMetric(
                            field(j), form,
                            field('Metric Description'), 'TopdownL1', ''
                        ))
                        infoname[field(j)] = form

        if l[0].startswith('Info'):
            info.append(PerfMetric(
                field('Level1'),
                find_form(),
                field('Metric Description'),
                field('Metric Group'),
                field('Locate-with')
            ))
            infoname[field('Level1')] = find_form()

        if l[0].startswith('Aux'):
            form = find_form()
            if form == '#NA':
                continue
            aux[field('Level1')] = form
            verboseprint('Adding aux', field('Level1'), form, file=sys.stderr)

    jo = []
    je = []
    if extrajson:
        je = json.loads(extrajson)
    if cstate:
        je.extend(cstate_json(cpu))

    for i in info:
        if i.name in ignore:
            verboseprint('Skipping', i.name, file=sys.stderr)
            continue

        form = i.form
        if form is None:
            verboseprint('no formula for', i.name, file=sys.stderr)
            continue
        if form == '#NA' or form == 'N/A':
            continue
        verboseprint(i.name, 'orig form', form, file=sys.stderr)

        if i.groups == '':
            if i.name in groups:
                i.groups = groups[i.name]

        def resolve_all(form: str, cpu: str):

            def fixup(form: str):
                form = check_expr(form)
                if (cpu == 'SPR'):
                    for j, r in spr_event_fixes:
                        form = form.replace(j, update_fix(r))
                elif (cpu == 'ICX'):
                    for j, r in icx_event_fixes:
                        form = form.replace(j, update_fix(r))
                else:
                    for j, r in event_fixes:
                        form = form.replace(j, update_fix(r))

                form = re.sub(r'\bTSC\b', 'msr@tsc@', form)
                if (unit == 'cpu_atom'):
                    form = re.sub(r'\bCLKS\b', 'CPU_CLK_UNHALTED.CORE', form)
                else:
                    form = re.sub(r'\bCLKS\b', 'CPU_CLK_UNHALTED.THREAD', form)
                form = form.replace('_PS', '')
                form = form.replace('\b1==1\b', '1')
                form = form.replace('#Memory == 1', '1' if memory else '0')
                form = form.replace('#EBS_Mode', '#core_wide < 1')

                form = re.sub(r'1e12', '1000000000000', form)
                form = re.sub(r':percore', '', form)
                form = re.sub(r':perf_metrics', '', form)
                pmu_prefix = 'cpu'
                if unit == 'cpu_core':
                    pmu_prefix = 'cpu_core'
                if unit == 'cpu_atom':
                    pmu_prefix = 'cpu_atom'
                changed = True
                event_pattern = r'[A-Z0-9_.]+'
                term_pattern = r'[a-z0-9\\=,]+'
                while changed:
                    changed = False
                    for match, replacement in [
                        (rf'{pmu_prefix}@(' + event_pattern + term_pattern +
                         r')@:sup', rf'{pmu_prefix}@\1@k'),
                        (rf'{pmu_prefix}@(' + event_pattern + term_pattern +
                         r')@:user', rf'{pmu_prefix}@\1@u'),
                        (rf'{pmu_prefix}@(' + event_pattern + term_pattern +
                         r')@:c(\d+)', rf'{pmu_prefix}@\1\\,cmask\\=\2@'),
                        (rf'{pmu_prefix}@(' + event_pattern + term_pattern +
                         r')@:u0x([A-Fa-f0-9]+)',
                         rf'{pmu_prefix}@\1\\,umask\\=0x\2@'),
                        (rf'{pmu_prefix}@(' + event_pattern + term_pattern +
                         r')@:i1', rf'{pmu_prefix}@\1\\,inv@'),
                        (rf'{pmu_prefix}@(' + event_pattern + term_pattern +
                         r')@:e1', rf'{pmu_prefix}@\1\\,edge@'),
                        ('(' + event_pattern + rf'):sup',
                         rf'{pmu_prefix}@\1@k'),
                        ('(' + event_pattern + rf'):user',
                         rf'{pmu_prefix}@\1@u'),
                        ('(' + event_pattern + rf'):c(\d+)',
                         rf'{pmu_prefix}@\1\\,cmask\\=\2@'),
                        ('(' + event_pattern + rf'):u0x([a-fA-F0-9]+)',
                         rf'{pmu_prefix}@\1\\,umask\\=0x\2@'),
                        ('(' + event_pattern + rf'):i1',
                         rf'{pmu_prefix}@\1\\,inv@'),
                        ('(' + event_pattern + rf'):e1',
                         rf'{pmu_prefix}@\1\\,edge@'),
                    ]:
                        new_form = re.sub(match, replacement, form,
                                          re.IGNORECASE)
                        changed = changed or new_form != form
                        form = new_form

                form = form.replace('##?(',
                                    '(')  # XXX hack, shouldn't be needed
                form = form.replace('##(', '(')  # XXX hack, shouldn't be needed
                form = check_expr(form)

                for i in range(5):
                    #  if #Model in ['KBLR' 'CFL' 'CLX'] else
                    m = re.match(r'(.*) if #Model in \[(.*)\] else (.*)', form)
                    if m:
                        if args.extramodel in m.group(2).replace("'",
                                                                 '').split():
                            form = m.group(1)
                        else:
                            form = m.group(3)

                    m = re.match(r'(.*) if #PMM_App_Direct else (.*)', form)
                    if m:
                        form = m.group(1)

                    m = re.match(r'(.*) if 1 else (.*)', form)
                    if m:
                        form = m.group(1)

                    m = re.match(r'(.*) if 0 else (.*)', form)
                    if m:
                        form = m.group(2)

                return check_expr(form)

            def resolve_aux(v: str):
                if v == '#Base_Frequency':
                    return v
                if v == '#SMT_on':
                    return v
                if v == '#core_wide':
                    return v
                if v == '#PERF_METRICS_MSR':
                    return v
                if v == '#Retired_Slots':
                    if 'ICL' in ratio_column[cpu]:
                        #"Retiring * SLOTS"
                        return '(' + infoname[
                            'Retiring'] + ')' + ' * ' + '(' + infoname[
                                'SLOTS'] + ')'
                    else:
                        return 'UOPS_RETIRED.RETIRE_SLOTS'
                if v == '#DurationTimeInSeconds':
                    return 'duration_time'
                if v == '#Model':
                    return '#Model'
                if v == '#NA':
                    return '0'
                if v[1:] in nodes:
                    child = nodes[v[1:]]
                else:
                    child = aux[v]
                badevent(child)
                child = fixup(child)
                #print(m.group(0), "=>", child, file=sys.stderr)
                return bracket(child)

            def resolve_info(v: str):
                if v in resolved:
                    return v
                if v in infoname:
                    return bracket(fixup(infoname[v]))
                elif v in nodes:
                    return bracket(fixup(nodes[v]))
                return v

            try:
                # iterate a few times to handle deeper nesting
                for j in range(10):
                    form = re.sub(r'#[a-zA-Z0-9_.]+',
                                  lambda m: resolve_aux(m.group(0)), form)
                    form = re.sub(r'[A-Z_a-z0-9.]+',
                                  lambda m: resolve_info(m.group(0)), form)
                badevent(form)
            except BadRef as e:
                verboseprint(
                    'Skipping ' + i.name + ' due to ' + e.name, file=sys.stderr)
                return ''

            form = fixup(form)
            return form

        def save_form(name, group, form, desc, locate, extra=''):
            if form == '':
                return
            if group.endswith(';'):
                group = group.rstrip(';')
            if group.startswith(';'):
                group = group[1:]
            group = group.strip()
            if 'PERF_METRICS' in form:
                return
            if 'Mispredicts_Resteers' in form:
                return
            verboseprint(name, form, file=sys.stderr)

            if (locate != ''):
                desc = desc + ', Sample with: ' + locate

            j = {
                'MetricName': name,
                'MetricExpr': form,
            }

            j1 = {
                'MetricName': name,
                'MetricExpr': form,
            }

            if len(group) > 0:
                j['MetricGroup'] = group
            if desc.count('.') > 1:
                sdesc = re.sub(r'(?<!i\.e)\. .*', '', desc)
                if extra:
                    sdesc = add_sentence(sdesc, extra)
                    desc = add_sentence(desc, extra)
                j['BriefDescription'] = sdesc
                if desc != sdesc:
                    j['PublicDescription'] = desc
            else:
                j['BriefDescription'] = desc

            if j['MetricName'] == 'Page_Walks_Utilization' or j[
                    'MetricName'] == 'Backend_Bound':
                j['MetricConstraint'] = 'NO_NMI_WATCHDOG'

            expr = j['MetricExpr']
            expr = re.sub(r':USER', ':u', expr)
            j['MetricExpr'] = check_expr(expr)

            if j['MetricName'] == 'Kernel_Utilization' or j[
                    'MetricName'] == 'Kernel_CPI':
                expr = j['MetricExpr']
                expr = re.sub(r':u', ':k', expr)
                expr = re.sub(r':SUP', ':k', expr)
                expr = re.sub(r'CPU_CLK_UNHALTED.REF_TSC',
                              'CPU_CLK_UNHALTED.THREAD', expr)
                j['MetricExpr'] = check_expr(expr)

            if extramodel == 'BDW-DE':
                if j['MetricName'] == 'Page_Walks_Utilization':
                    j['MetricExpr'] = (
                        '( cpu@ITLB_MISSES.WALK_DURATION\\,cmask\\=1@ + '
                        'cpu@DTLB_LOAD_MISSES.WALK_DURATION\\,cmask\\=1@ + '
                        'cpu@DTLB_STORE_MISSES.WALK_DURATION\\,cmask\\=1@ + '
                        '7 * ( DTLB_STORE_MISSES.WALK_COMPLETED + '
                        'DTLB_LOAD_MISSES.WALK_COMPLETED + '
                        'ITLB_MISSES.WALK_COMPLETED ) ) / '
                        'CPU_CLK_UNHALTED.THREAD')
                if j['MetricName'] == 'Page_Walks_Utilization_SMT':
                    j['MetricExpr'] = (
                        '( cpu@ITLB_MISSES.WALK_DURATION\\,cmask\\=1@ + '
                        'cpu@DTLB_LOAD_MISSES.WALK_DURATION\\,cmask\\=1@ + '
                        'cpu@DTLB_STORE_MISSES.WALK_DURATION\\,cmask\\=1@ + '
                        '7 * ( DTLB_STORE_MISSES.WALK_COMPLETED + '
                        'DTLB_LOAD_MISSES.WALK_COMPLETED + '
                        'ITLB_MISSES.WALK_COMPLETED ) ) / ( ( '
                        'CPU_CLK_UNHALTED.THREAD / 2 ) * ( 1 + '
                        'CPU_CLK_UNHALTED.ONE_THREAD_ACTIVE / '
                        'CPU_CLK_UNHALTED.REF_XCLK ) )')

            if unit:
                j['Unit'] = unit

            tmp_expr = j['MetricExpr']
            global counts
            counts = 0
            re.sub(r'[a-zA-Z_.]+', lambda m: count_metric_events(m.group(0)),
                   tmp_expr)

            if expr_events:
                if counts >= int(expr_events):
                    resolved.append(j['MetricName'])
            else:
                resolved.append(j['MetricName'])
            jo.append(j)

            if j['MetricName'] == "Socket_CLKS":
                j1['BriefDescription'] = "Uncore frequency per die [GHZ]"
                j1['MetricExpr'] = "Socket_CLKS / #num_dies / duration_time / 1000000000"
                j1['MetricGroup'] = "SoC"
                j1['MetricName'] = "UNCORE_FREQ"
                tmp_expr = j['MetricExpr']
                expr = j1['MetricExpr']
                expr = re.sub(r'Socket_CLKS',tmp_expr,expr)
                j1['MetricExpr'] = check_expr(expr)
                jo.append(j1)

        form = resolve_all(form, cpu)
        save_form(i.name, i.groups, form, i.desc, i.locate)

    jo = jo + je

    outfile.write(
        json.dumps(jo, sort_keys=True, indent=4, separators=(',', ': ')))
    outfile.write('\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cpu')
    ap.add_argument('csvfile', type=argparse.FileType('r'))
    ap.add_argument('--output', type=argparse.FileType('w'), default=sys.stdout)
    ap.add_argument('--verbose', action='store_true')
    ap.add_argument('--memory', action='store_true')
    ap.add_argument('--cstate', action='store_true')
    ap.add_argument('--expr-events')
    ap.add_argument('--extramodel')
    ap.add_argument('--extrajson', type=argparse.FileType('r'))
    ap.add_argument('--unit')
    args = ap.parse_args()

    extract_tma_metrics(args.csvfile, args.cpu, args.extrajson, args.cstate,
                        args.extramodel, args.unit, args.expr_events,
                        args.memory, args.verbose, args.output)


if __name__ == '__main__':
    main()
