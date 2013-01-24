#!/usr/bin/env python3

# This script reads a reichelt order list file and outputs text suitable for reichelt's shopping cart import thingy

import argparse
from bs4 import BeautifulSoup as bs
import string
import sys
import time
from os import path
try:
    import re2 as re
except ImportError:
	import re

parser = argparse.ArgumentParser(description='Throw text files at reichelt!')
parser.add_argument('csvfile', nargs='?', default=sys.stdin, type=argparse.FileType('r'))
args = parser.parse_args()

#Decipher input
items = []
linenum = 0
total_items = 0
for l in args.csvfile:
	linenum += 1
	if 'Nicht von Reichelt' in l:
		break
	if not l.startswith('#'):
		d = l.split('\t')[:3]
		if len(d) >= 2:
			(count, itemid) = d[:2]
			items.append((count, itemid.strip()))
			total_items += int(count)
			print('{};{}'.format(itemid.strip(), count))

print('Read ', len(items), ' items totalling ', total_items, 'parts', file=sys.stderr)

