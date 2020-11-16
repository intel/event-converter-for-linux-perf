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

event-oprofile
  - convert a CSV or JSON PMU event table to oprofile format generic json version
  - event-oprofile cpu.csv|cpu.json cpu

evj2csv
  - convert json event format to csv

EXTRACTMETRICS
  - EXTRACTMETRICS PublicTMASpreadsheet.CSV
  - see example below

extract-tmam-metrics.py
  - extract metrics for cpu from TMAM spreadsheet and generate JSON metrics files
  - extract-tmam-metrics.py CPU tmam-csv-file.csv > cpu-metrics.json

gen-metrics
  - generate json metric files in perf tree from TMAM
  - gen-metrics TMEM-file linux-tree

json2csv
  - convert json to equivalent CSV (with tabs)

json-remove-events
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

uncore_csv_json
  - generate split uncore json from csv spreadsheet input
  - uncore_csv_json csv orig-pme-json targetdir
  - see example below

Examples:
---------
1. Generate core event json for one specified platform, such as skylakex.

$ python json-to-perf-json.py --outdir ./skx-output skylakex_core_v1.24.json
cache.json
floating-point.json
frontend.json
memory.json
other.json
pipeline.json
virtual-memory.json

skylakex_core_v1.24.json is downloaded from https://download.01.org/perfmon/.

2. Generate uncore event json

$ python uncore_csv_json --all perf-uncore-events-clx.csv cascadelakex_uncore_v1.11.json ./clx-output cascadelakex_uncore_v1.11_experimental.json
......
generating Uncore-Memory
generating Uncore-Other

cascadelakex_uncore_v1.11.json and cascadelakex_uncore_v1.11_experimental.json
are downloaded from https://download.01.org/perfmon/.

3. Generate metrics for CLX

$ python extract-tmam-metrics.py CLX TMA_Metrics.csv

TMA_Metrics.csv is downloaded from //download.01.org/perfmon/.

4. Generate metrics for all archs
$ ./EXTRACTMETRICS TMA_Metrics.csv

Andi Kleen <ak@linux.intel.com>
Liang Kan <kan.liang@intel.com>
Jin Yao <yao.jin@linux.intel.com>
