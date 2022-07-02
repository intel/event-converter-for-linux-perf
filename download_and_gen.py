#!/usr/bin/python
import argparse
import collections
import csv
import io
import json
import os
import re
import uncore_csv_json
import urllib.request
import importlib
from itertools import takewhile
from typing import (Dict, DefaultDict, Sequence, Set)

json_to_perf_json = importlib.import_module('json-to-perf-json')
hybrid_json_to_perf_json = importlib.import_module('hybrid-json-to-perf-json')
extract_tma_metrics = importlib.import_module('extract-tma-metrics')


class Model:
    shortname: str
    longname: str
    version: str
    files: Dict[str, str]
    models: Sequence[str]

    def __init__(self, shortname: str, longname: str, version: str,
                 models: Set[str], files: Dict[str, str]):
        self.shortname = shortname
        self.longname = longname.lower()
        self.version = version
        self.models = sorted(models)
        self.files = files

    def __lt__(self, other):
        # Sort by model number: min(self.models) < min(other.models)
        return self.longname < other.longname

    def __str__(self):
        return f'{self.shortname} / {self.longname}\n\tmodels={self.models}\n\t' + '\n\t'.join(
            [f'{type}_url = {url}' for (type, url) in self.files.items()])

    def to_perf_json(self, outdir: str):
        # Core event files.
        if 'atom' in self.files:
            with urllib.request.urlopen(self.files['atom']) as atom_json:
                with urllib.request.urlopen(self.files['core']) as core_json:
                    hybrid_json_to_perf_json.hybrid_json_to_perf_json(
                        atom_json, core_json, outdir)
        else:
            with urllib.request.urlopen(self.files['core']) as core_json:
                json_to_perf_json.json_to_perf_json(core_json, outdir, '')

        # Uncore event files.
        if 'uncore' in self.files:
            uncore_csv_file = f'perf-uncore-events-{self.shortname.lower()}.csv'
            if os.path.exists(uncore_csv_file):
                uncore_csv = open(uncore_csv_file, 'r')
            else:
                uncore_csv = io.StringIO('')
            with urllib.request.urlopen(self.files['uncore']) as uncore_json:
                if 'uncore experimental' in self.files:
                    with urllib.request.urlopen(
                            self.files['uncore experimental']
                    ) as experimental_json:
                        uncore_csv_json.uncore_csv_json(
                            csvfile=uncore_csv,
                            jsonfile=uncore_json,
                            extrajsonfile=experimental_json,
                            targetdir=outdir,
                            all_events=True)
                else:
                    uncore_csv_json.uncore_csv_json(
                        csvfile=uncore_csv,
                        jsonfile=uncore_json,
                        extrajsonfile=None,
                        targetdir=outdir,
                        all_events=True)
        # TMA metrics.
        tma_cpu = extract_tma_metrics.find_tma_cpu(self.shortname)
        if not tma_cpu:
            return
        metrics_file = f'{outdir}/{self.shortname.replace("-","").lower()}-metrics.json'
        with urllib.request.urlopen(self.files['tma metrics']) as tma_metrics:
            tma_metrics_lines = [
                l.decode('utf-8') for l in tma_metrics.readlines()
            ]
            outfile = open(metrics_file, 'w')
            if 'atom' in self.files:
                core_json = io.StringIO()
                extract_tma_metrics.extract_tma_metrics(
                    csvfile=tma_metrics_lines,
                    cpu=tma_cpu,
                    extrajson=None,
                    cstate=False,
                    extramodel=self.shortname,
                    unit='cpu_core',
                    expr_events='100',
                    memory=True,
                    verbose=False,
                    outfile=core_json)
                atom_json = io.StringIO()
                with urllib.request.urlopen(
                        self.files['e-core tma metrics']) as e_core_tma_metrics:
                    e_core_tma_metrics_lines = [
                        l.decode('utf-8')
                        for l in e_core_tma_metrics.readlines()
                    ]
                    e_core_tma_cpu = {
                        'ADL': 'GRT',
                    }[self.shortname]
                    extract_tma_metrics.extract_tma_metrics(
                        csvfile=e_core_tma_metrics_lines,
                        cpu=e_core_tma_cpu,
                        extrajson=None,
                        cstate=True,
                        extramodel=e_core_tma_cpu,
                        unit='cpu_atom',
                        expr_events='100',
                        memory=True,
                        verbose=False,
                        outfile=atom_json)
                jo = json.loads(core_json.getvalue())
                for event in json.loads(atom_json.getvalue()):
                    jo.append(event)
                outfile.write(
                    json.dumps(
                        jo, sort_keys=True, indent=4, separators=(',', ': ')))
                outfile.write('\n')
            else:
                extract_tma_metrics.extract_tma_metrics(
                    csvfile=tma_metrics_lines,
                    cpu=tma_cpu,
                    extrajson=None,
                    cstate=True,
                    extramodel=self.shortname,
                    unit='',
                    expr_events='100',
                    memory=True,
                    verbose=False,
                    outfile=outfile)

        # Additional metrics
        broken_extra_metrics = {
            'BDX': [
                # Missing #SYSTEM_TSC_FREQ
                'cpu_operating_frequency',
            ],
            'CLX': [
                # Missing #SYSTEM_TSC_FREQ
                'cpu_operating_frequency',
                # Missing UNC_IIO_PAYLOAD_BYTES_IN.MEM_READ.PART1
                'io_bandwidth_read',
                # Missing UNC_IIO_PAYLOAD_BYTES_IN.MEM_WRITE.PART1
                'io_bandwidth_write',
                # Missing cha/unc_cha_tor_occupancy.ia_miss/
                'llc_data_read_demand_plus_prefetch_miss_latency',
                'llc_data_read_demand_plus_prefetch_miss_latency_for_local_requests',
                'llc_data_read_demand_plus_prefetch_miss_latency_for_remote_requests',
            ],
            'ICX': [
                # Missing #SYSTEM_TSC_FREQ
                'cpu_operating_frequency',
                # Broken event EXE_ACTIVITY.3_PORTS_UTIL:u0x80
                'tma_ports_utilization_percent',
                # Syntax error
                'tma_backend_bound_percent',
                'tma_bad_speculation_percent',
                'tma_branch_mispredicts_percent',
                'tma_core_bound_percent',
                'tma_machine_clears_percent',
                'tma_memory_bound_percent',
            ],
            'SKX': [
                # Missing #SYSTEM_TSC_FREQ
                'cpu_operating_frequency',
                # Missing UNC_IIO_PAYLOAD_BYTES_IN.MEM_READ.PART1
                'io_bandwidth_read',
                # Missing UNC_IIO_PAYLOAD_BYTES_IN.MEM_WRITE.PART1
                'io_bandwidth_write',
                # Missing cha/unc_cha_tor_occupancy.ia_miss/
                'llc_data_read_demand_plus_prefetch_miss_latency',
                'llc_data_read_demand_plus_prefetch_miss_latency_for_local_requests',
                'llc_data_read_demand_plus_prefetch_miss_latency_for_remote_requests',
            ],
            'SPR': [
                # Missing #SYSTEM_TSC_FREQ
                'cpu_operating_frequency',
                # Broken event AMX_OPS_RETIRED.BF16:c1
                'tma_fp_arith_percent',
                'tma_other_light_ops_percent',
                # Broken event EXE_ACTIVITY.3_PORTS_UTIL:u0x80 and
                # EXE_ACTIVITY.2_PORTS_UTIL:u0xc
                'tma_ports_utilization_percent',
            ],
        }
        if 'extra metrics' in self.files:
            with urllib.request.urlopen(
                    self.files['extra metrics']) as extra_metrics_json:
                metrics_json = open(metrics_file, 'r')
                metrics = json.load(metrics_json)
                extra_metrics = json.load(extra_metrics_json)
                for extra_metric in extra_metrics:
                    if self.shortname in broken_extra_metrics and extra_metric[
                            'MetricName'].lower() in broken_extra_metrics[
                                self.shortname]:
                        continue
                    metrics = [
                        x for x in metrics if x['MetricName'].lower() !=
                        extra_metric['MetricName'].lower()
                    ]
                    metrics.append(extra_metric)
                outfile = open(metrics_file, 'w')
                outfile.write(
                    json.dumps(
                        metrics,
                        sort_keys=True,
                        indent=4,
                        separators=(',', ': ')))
                outfile.write('\n')

    def mapfile_line(self):
        if len(self.models) == 1:
            ret = min(self.models)
        else:
            prefix = ''.join(
                c[0] for c in takewhile(lambda x: all(x[0] == y for y in x
                                                     ), zip(*self.models)))
            if len(min(self.models)) - len(prefix) > 1:
                start_bracket = '('
                end_bracket = ')'
                seperator = '|'
            else:
                start_bracket = '['
                end_bracket = ']'
                seperator = ''
            ret = prefix + start_bracket
            first = True
            for x in self.models:
                if not first:
                    ret += seperator
                ret += x[len(prefix):]
                first = False
            ret += end_bracket
        ret += f',{self.version.lower()},{self.longname},core'
        return ret


class Mapfile:
    archs: Sequence[Model]

    def __init__(self, base_url: str, metrics_url: str):
        self.archs = []
        longnames: Dict[str, str] = {}
        models: DefaultDict[str, Set[str]] = collections.defaultdict(set)
        files: Dict[str, Dict[str, str]] = collections.defaultdict(dict)
        versions: Dict[str, str] = {}
        with urllib.request.urlopen(base_url + '/mapfile.csv') as mapfile_csv:
            mapfile_csv_lines = [
                l.decode('utf-8') for l in mapfile_csv.readlines()
            ]
            mapfile = csv.reader(mapfile_csv_lines)
            first_row = True
            for (family_model, version, path, event_type, core_type,
                 native_model_id, core_role_name) in mapfile:
                if first_row:
                    assert family_model == 'Family-model'
                    assert version == 'Version'
                    assert path == 'Filename'
                    assert event_type == 'EventType'
                    assert core_type == 'Core Type'
                    assert native_model_id == 'Native Model ID'
                    assert core_role_name == 'Core Role Name'
                    first_row = False
                    continue
                shortname = re.sub(r'/(.*)/.*', r'\1', path)
                longname = re.sub(rf'/{shortname}/([^_]*)_.*', r'\1', path)
                url = base_url + path

                # Bug fixes:
                if shortname == 'SNR' and event_type == 'uncore' and 'experimental' in path:
                    event_type = 'uncore experimental'

                # Workarounds:
                if event_type == 'hybridcore':
                    event_type = 'core' if core_role_name == 'Core' else 'atom'
                if shortname == 'KNM':
                    # The files for KNL and KNM are the same as are
                    # the longnames. We don't want the KNM shortname
                    # but do want the family_model.
                    models['KNL'].add(family_model)
                    continue

                if not shortname in longnames:
                    longnames[shortname] = longname
                else:
                    assert longnames[shortname] == longname
                if not shortname in versions:
                    versions[shortname] = version
                else:
                    assert versions[shortname] == version
                models[shortname].add(family_model)
                if shortname in files and event_type in files[shortname]:
                    assert files[shortname][event_type] == url, \
                        f'Expected {shortname}/{longname} to have just 1 {event_type} url {files[shortname][event_type]} but found {url}'
                else:
                    files[shortname][event_type] = url

        for (shortname, longname) in longnames.items():
            files[shortname]['tma metrics'] = base_url + '/TMA_Metrics-full.csv'
            if 'atom' in files[shortname]:
                files[shortname][
                    'e-core tma metrics'] = base_url + '/E-core_TMA_Metrics.csv'
            cpu_metrics_url = f'{metrics_url}/{shortname}/metrics/perf/{shortname.lower()}_metric_perf.json'
            try:
                urllib.request.urlopen(cpu_metrics_url)
                files[shortname]['extra metrics'] = cpu_metrics_url
            except:
                pass

            self.archs += [
                Model(shortname, longname, versions[shortname],
                      models[shortname], files[shortname])
            ]
        self.archs.sort()

    def __str__(self):
        result = ''
        for model in self.archs:
            result += str(model) + '\n'
        return result

    def to_perf_json(self, outdir: str):
        gen_mapfile = open(f'{outdir}/mapfile.csv', 'w')
        for model in self.archs:  #[x for x in self.archs if x.shortname == 'TGL']:
            print(f'Generating json for {model.longname}')
            modeldir = outdir + '/' + model.longname
            os.system(f'mkdir -p {modeldir}')
            model.to_perf_json(modeldir)
            gen_mapfile.write(model.mapfile_line() + '\n')


def generate_all_event_json(url: str, metrics_url: str, outdir: str):
    mapfile = Mapfile(url, metrics_url)

    os.system(f'mkdir -p {outdir}')
    mapfile.to_perf_json(outdir)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default='https://download.01.org/perfmon')
    ap.add_argument(
        '--metrics-url',
        default='https://raw.githubusercontent.com/intel/perfmon-metrics/main')
    ap.add_argument('--outdir', default='perf')
    args = ap.parse_args()

    generate_all_event_json(args.url, args.metrics_url, args.outdir)


if __name__ == '__main__':
    main()
