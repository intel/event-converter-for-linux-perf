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
from typing import (Any, Dict, DefaultDict, Sequence, Set)

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

    def __lt__(self, other: Any) -> bool:
        # Sort by model number: min(self.models) < min(other.models)
        return self.longname < other.longname

    def __str__(self):
        return f'{self.shortname} / {self.longname}\n\tmodels={self.models}\n\t' + '\n\t'.join(
            [f'{type}_url = {url}' for (type, url) in self.files.items()])

    def to_perf_json(self, outdir: str, csvdir: str):
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
            uncore_csv_file = f'{csvdir}/perf-uncore-events-{self.shortname.lower()}.csv'
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
                            all_events=True,
                            verbose=False)
                else:
                    uncore_csv_json.uncore_csv_json(
                        csvfile=uncore_csv,
                        jsonfile=uncore_json,
                        extrajsonfile=None,
                        targetdir=outdir,
                        all_events=True,
                        verbose=False)
        # TMA metrics.
        tma_cpu = extract_tma_metrics.find_tma_cpu(self.shortname)
        if not tma_cpu:
            return
        metrics_file = f'{outdir}/{self.shortname.replace("-","").lower()}-metrics.json'
        with urllib.request.urlopen(self.files['tma metrics']) as tma_metrics:
            tma_metrics_lines = [
                l.decode('utf-8') for l in tma_metrics.readlines()
            ]
            outfile = open(metrics_file, 'w', encoding='ascii')
            if 'atom' in self.files:
                core_json = io.StringIO()
                extract_tma_metrics.extract_tma_metrics(
                    csvfile=tma_metrics_lines,
                    cpu=tma_cpu,
                    extrajson=None,
                    cstate=False,
                    extramodel=self.shortname,
                    unit='cpu_core',
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
                    memory=True,
                    verbose=False,
                    outfile=outfile)

        # Additional metrics
        broken_extra_metrics = {}
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
                    if any(extra_metric['MetricName'].lower() == x['MetricName'].lower() for x in metrics):
                        # Prefer existing metrics over those in extra
                        # metrics as the existing metrics may be
                        # written in terms of each other and have
                        # consistent units.
                        continue
                    metrics.append(extra_metric)
                outfile = open(metrics_file, 'w', encoding='ascii')
                outfile.write(
                    json.dumps(
                        metrics,
                        sort_keys=True,
                        indent=4,
                        separators=(',', ': ')))
                outfile.write('\n')

    def mapfile_line(self) -> str:
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
        print(f'Analyzing {base_url}/mapfile.csv')
        with urllib.request.urlopen(base_url + '/mapfile.csv') as mapfile_csv:
            mapfile_csv_lines = [
                l.decode('utf-8') for l in mapfile_csv.readlines()
            ]
            mapfile = csv.reader(mapfile_csv_lines)
            first_row = True
            for l in mapfile:
                while len(l) < 7:
                    # Fix missing columns.
                    l.append('')
                family_model, version, path, event_type, core_type, native_model_id, core_role_name = l
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
                if shortname == 'ADL' and event_type == 'core':
                    # ADL GenuineIntel-6-BE only has atom cores and so
                    # they don't set event_type to 'hybridcore' but
                    # 'core' leading to ADL having multiple core
                    # paths. Avoid this by setting the type back to
                    # atom.
                    assert 'gracemont' in path
                    event_type = 'atom'
                    core_role_name = 'Atom'

                # Workarounds:
                if event_type == 'hybridcore':
                    event_type = 'core' if core_role_name == 'Core' else 'atom'
                if shortname == 'KNM':
                    # The files for KNL and KNM are the same as are
                    # the longnames. We don't want the KNM shortname
                    # but do want the family_model.
                    models['KNL'].add(family_model)
                    continue

                if shortname not in longnames:
                    longnames[shortname] = longname
                else:
                    assert longnames[shortname] == longname
                if shortname not in versions:
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

    def to_perf_json(self, outdir: str, csvdir: str):
        gen_mapfile = open(f'{outdir}/mapfile.csv', 'w', encoding='ascii')
        for model in self.archs:
            print(f'Generating json for {model.longname}')
            modeldir = outdir + '/' + model.longname
            os.system(f'mkdir -p {modeldir}')
            model.to_perf_json(modeldir, csvdir)
            gen_mapfile.write(model.mapfile_line() + '\n')

    def download(self, base_url: str, metrics_url: str, outdir: str):
        os.system(f'mkdir -p {outdir}/01')
        with open(f'{outdir}/01/mapfile.csv', 'w', encoding='ascii') as out_mapfile:
            with urllib.request.urlopen(base_url + '/mapfile.csv') as in_mapfile:
                for l in in_mapfile.readlines():
                    out_mapfile.write(l.decode('ascii'))
        files = set()
        for model in self.archs:
            for short, url in model.files.items():
                files.add(url)
        for url in sorted(files):
            if base_url in url:
                out_path = outdir + '/01' + url.removeprefix(base_url)
            else:
                out_path = outdir + '/github' + url.removeprefix(metrics_url)
            print(f'Downloading:\n\t{url} to\n\t{out_path}')
            os.system(f'mkdir -p {os.path.dirname(out_path)}')
            with open(out_path, 'w', encoding='ascii') as out_json:
                with urllib.request.urlopen(url) as in_json:
                    for l in in_json.readlines():
                        ascii_line = re.sub('\xae', '(R)', l.decode('utf-8'))
                        ascii_line = re.sub('\u2122', '(TM)', ascii_line)
                        ascii_line = re.sub('\uFEFF', '', ascii_line)
                        out_json.write(ascii_line)
        print('Now run with: download_and_gen.py ' +
              f'--url=file://{os.path.abspath(outdir)}/01 ' +
              f'--metrics-url=file://{os.path.abspath(outdir)}/github')

def generate_all_event_json(url: str, metrics_url: str, outdir: str, csvdir: str):
    mapfile = Mapfile(url, metrics_url)

    os.system(f'mkdir -p {outdir}')
    mapfile.to_perf_json(outdir, csvdir)

def hermetic_download(url: str, metrics_url: str, outdir: str):
    mapfile = Mapfile(url, metrics_url)

    os.system(f'mkdir -p {outdir}')
    mapfile.download(url, metrics_url, outdir)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default='https://download.01.org/perfmon')
    ap.add_argument(
        '--metrics-url',
        default='https://raw.githubusercontent.com/intel/perfmon-metrics/main')
    ap.add_argument('--csvdir', default='.', help='Path for uncore CSV files')
    ap.add_argument('--outdir', default='perf')
    ap.add_argument('--hermetic-download', action='store_true',
                    help="""Download necessary files rather than generating perf json.
The downloaded files can later be passed to the --url/--metrics-url options""")
    args = ap.parse_args()

    if args.hermetic_download:
        hermetic_download(args.url, args.metrics_url, args.outdir)
    else:
        generate_all_event_json(args.url, args.metrics_url, args.outdir, args.csvdir)


if __name__ == '__main__':
    main()
