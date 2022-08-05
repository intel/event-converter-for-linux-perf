#!/usr/bin/python

import argparse
import json
import sys

def main():
  ap = argparse.ArgumentParser()
  ap.add_argument(
      'infile',
      type=argparse.FileType('r'),
      help='01.org style json to remove deprecrated events from')
  ap.add_argument(
      'outfile',
      nargs='?',
      type=argparse.FileType('w'),
      help='Generated file name',
      default=sys.stdout)
  args = ap.parse_args()

  args.outfile.write(
      json.dumps([
          x for x in json.load(args.infile)
          if 'Deprecated' not in x or x['Deprecated'] != '1'
      ], sort_keys=True, indent=4, separators=(',', ': ')))


if __name__ == '__main__':
  main()
