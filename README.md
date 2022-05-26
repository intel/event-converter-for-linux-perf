# event-converter-for-linux-perf

Intel publishes PMU events JSON files on 01.org.
(https://download.01.org/perfmon/)

This project converts the Intel published events to Linux perf format
events thus Linux perf can use Intel specific PMU events.

This project uses "BSD clause 3" license (see COPYING).

Scripts usage:
--------------
csv-field.py
  - print csv fields from csv
  - csv-field.py field1 ... fieldN < csv

event-oprofile.py
  - convert a CSV or JSON PMU event table to oprofile format generic json version
  - event-oprofile.py cpu.csv|cpu.json cpu

evj2csv.py
  - convert json event format to csv

EXTRACTMETRICS
  - EXTRACTMETRICS PublicTMASpreadsheet.CSV
  - see example below

extract-tma-metrics.py
  - extract metrics for cpu from TMA spreadsheet and generate JSON metrics files
  - extract-tma-metrics.py CPU tma-csv-file.csv > cpu-metrics.json

gen-metrics
  - generate json metric files in perf tree from TMA
  - gen-metrics TMEM-file linux-tree

json2csv.py
  - convert json to equivalent CSV (with tabs)

json-remove-events.py
  - remove selected events from json file

json-to-perf-json.py
  - generate split perf json files from a single perf json files
  - see example below

line-len
  - print line lengths of file (to workaround git send-email limitations)

merge-json
  - merge json event files
  - merge-json file1.json file2... > merged.json

op-all-events
  - print all oprofile events
  - ophelp --xml | op-all-events

pd-shell
  - open a pandas shell for json file (need pandas)

print-all
  - print all events from a json event file in perf format

print-alone
  - print events with "TakenAlone" set

print-datala
  - print all datala events from a json event file
  - print-datala file.json

print-expr
  - print all events from a json event matching expr (need pandas)
  - print-expr "pandas expr" file.json

print-names
  - print event name

print-pebs
  - print all pebs events from a json event file in perf format
  - print-pebs file.json

print-pebs-raw
  - print all pebs events raw encoding from a json event file in perf format
  - print-pebs-raw file.json

revev
  - print names for hex events
  - revev jsonfile hex-event ...

rev-event
  - print all events from a json event file in perf format (no special)

uncore_csv_json.py
  - generate split uncore json from csv spreadsheet input
  - uncore_csv_json.py csv orig-pme-json targetdir

hybrid-json-to-perf-json.py
  - create atom and core hybrid event list JSONs
  - hybrid-json-to-perf-json.py atomjson corejson
  - see example below


Examples:
---------
1. Generate core event json for one specified platform, such as skylakex.

$ python3 json-to-perf-json.py --outdir ./skx-output skylakex_core_v1.24.json
cache.json
floating-point.json
frontend.json
memory.json
other.json
pipeline.json
virtual-memory.json

skylakex_core_v1.24.json is downloaded from https://download.01.org/perfmon/.

2. Generate core event JSON for the Hybrid platforms, such as Alderlake

$ python3 hybrid-json-to-perf-json.py alderlake_gracemont_core_v1.06.json alderlake_goldencove_core_v1.06.json --outdir out

The jsons "cache.json, floating-point.json, frontend.json, memory.json,
other.json, pipeline.json, virtual-memory.json" will be created under directory
"out".

In each json, it contains both atom event and core event.

Both alderlake_gracemont_core_v1.06.json and alderlake_goldencove_core_v1.06.json are
downloaded from https://download.01.org/perfmon/.

3. Generate uncore event json

$ python3 uncore_csv_json.py --all perf-uncore-events-clx.csv cascadelakex_uncore_v1.11.json ./clx-output cascadelakex_uncore_v1.11_experimental.json
......
generating Uncore-Memory
generating Uncore-Other

cascadelakex_uncore_v1.11.json and cascadelakex_uncore_v1.11_experimental.json
are downloaded from https://download.01.org/perfmon/.

4. Generate metrics for CLX

$ python3 extract-tma-metrics.py CLX TMA_Metrics.csv

TMA_Metrics.csv is downloaded from //download.01.org/perfmon/.

5. Generate metrics for non-hybrid platforms

$ ./EXTRACTMETRICS TMA_Metrics.csv

6. Generate metrics for hybrid platforms

$ ./EXTRACTMETRICS-HYBRID TMA_Metrics-full.csv  E-core_TMA_Metrics.csv

7. Download the latest event list and metrics JSON files from https://download.01.org/perfmon/
   Generate perf events and metrics for all platforms.

$ ./download_and_gen.sh


Andi Kleen <ak@linux.intel.com>
Liang Kan <kan.liang@intel.com>
Xing Zhengjun <zhengjun.xing@linux.intel.com>
