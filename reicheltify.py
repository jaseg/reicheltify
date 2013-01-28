#!/usr/bin/env python3

#This script uploads a reichelt order list to a certain reichelt session's shopping cart

import argparse
from urllib import (parse, request, error)
from http import cookiejar
from http import client
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
parser.add_argument('-s', '--session', type=str, default=None, help='The session id of the reichelt session')
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

print('Read ', len(items), ' items totalling ', total_items, 'parts')

session = args.session
if not session:
	print('No session ID given.')
	exit(1)
	#Get a session ID
	#FIXME this does not work properly atm
	srq = request.Request('http://www.reichelt.de/')
	sres = request.urlopen(srq)
	session = re.search('SID=([0-9a-zA-Z-]*)', sres.read().decode('iso-8859-1')).group(1)
	print('Requested a session ID: {}'.format(session))

def post_items(items, session):
	#itemid needs to be encoded in iso-8859-1/latin-1 because that's what reichelt uses
	# ('Anzahl_Unknown[%d]' % i, count) for i, (count, _) in enumerate(items), 
	rd = {}
	for i, (count, itemid) in enumerate(items):
		rd['Anzahl_Unknown[%d]' % i] = count
		rd['Input_Unknown[%d]' % i] = itemid.encode('iso-8859-1')
	#pd = {'exwk': rd, 'filename': 'foo', 'Hochladen': 'Hochladen'}
	rq = request.Request('http://www.reichelt.de/index.html?;ACTION=19;LA=5012;SID={}'.format(args.session), data=parse.urlencode(rd).encode('iso-8859-1'))
	#page = post_multipart('http://www.reichelt.de/', '/Warenkorb/5/index.html?;ACTION=19;LA=5012;SID={}'.format(args.session), [('Hochladen', 'Hochladen'), ('filename', 'foo')], [('exwk', 'foo', rd)])
	res = request.urlopen(rq)
	page = res.read()
	pool = bs(page)
	failed = pool.find(id='CSSDIVID_in')
	if failed:
		for r in failed.find_all('tr'):
			os = r.find_all('option')
			if len(os):
				print('Not found:', os[0].text.rstrip('=>Bitte auswählen'))
				for o in os[1:]:
					print('\tDid you mean: ', o.text)
			else:
				o = r.find('input', {'class': 'artnr'})
				print('Part number corrected, please repost:', o['value'])
	
	print(*[ 'Item unavailable: ' + el.parent.parent.parent.find_all('a')[1].text for el in pool.find_all('p', {'style': 'color: red; font-size: 10px;'}) ], sep='\n')

post_items(items[0:200], session)
#for count, itemid in items[0:50]:
#	 print(count,'\t',itemid)

#NOTE Use the following lines instead of the line above in case reichelt.de barfs with a 500 error or empty response.
#def chunks(seq, size):
#	return ((idx, seq[off:off+size]) for (idx, off) in enumerate(range(0, len(seq), size)))

#CHUNKSIZE = 100

#for i, chunk in chunks(items, CHUNKSIZE):
#	print('Posting chunk {}/{}'.format(i+1, int(len(items)/CHUNKSIZE+1)))
#	post_items(chunk, session)

