#!/usr/bin/env python3

# THIS SCRIPT IS DEPRECATED. DO NOT USE!
# I still keep it here because it is kind of interesting.
# This script uploads a reichelt order list to a reichelt shopping cart by posting it in chunks to the reichelt bulk order page.

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

#NOTE: This script currently does not work as it is supposed to. reichelt.de reliably starts throwing HTTP/500 errors somewhere around 100 articles posted.

parser = argparse.ArgumentParser(description='Throw text files at reichelt!')
parser.add_argument('csvfile', nargs='?', default=sys.stdin, type=argparse.FileType('r'))
parser.add_argument('-s', '--session', type=str, default=None, help='The session id of the reichelt session')
args = parser.parse_args()

CHUNKSIZE = 10

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
items=items[:29]

print('Read ', len(items), ' items totalling ', total_items, 'parts')

session = args.session
if not session:
	#Get a session ID
	srq = request.Request('http://www.reichelt.de/')
	sres = request.urlopen(srq)
	session = re.search('SID=([0-9a-zA-Z-]*)', sres.read().decode('iso-8859-1')).group(1)
	print('Requested a session ID: {}'.format(session))

def chunks(seq, size):
	return ((idx, seq[off:off+size]) for (idx, off) in enumerate(range(0, len(seq), size)))

def post_items(items, session):
	pd = {'SORT': 'user', 'LINES': len(items)}

	for i, (count, itemid) in enumerate(items):
		#itemid needs to be encoded in iso-8859-1/latin-1 because that's what reichelt uses
		pd['DirectInput_[{}]'.format(i)]=itemid.encode('iso-8859-1')
		pd['DirectInput_count_[{}]'.format(i)]=count

	rq = request.Request('http://www.reichelt.de/Warenkorb/5/index.html?;ACTION=5;LA=5;SHOW=1;LINES={};SID={}'.format(len(items), args.session), data=parse.urlencode(pd).encode('iso-8859-1'))
	res = request.urlopen(rq)
	page = res.read()
	pool = bs(page)
	if pool.find('li', attrs={'class': 'di_liste_not_found'}):
		results = pool.find('div', attrs={'class': 'di_artikellist'}).findAll('ul', attrs={'class': 'di_liste'})
		for itemelem in results:
			failed_id = itemelem.find('input')['value']
			print('Item not found: ', failed_id, file=sys.stderr)
			sys.stderr.flush()

sleeptime =0
for i, chunk in chunks(items, CHUNKSIZE):
	print('Posting chunk {}/{}'.format(i+1, int(len(items)/CHUNKSIZE+1)))
	posted = False
	while not posted:
		time.sleep(sleeptime)
		try:
			post_items(chunk, session)
			posted = True
			sleeptime = 4
		except client.BadStatusLine:
			print('Bad status line error, ignoring', file=sys.stderr)
			sleeptime = 20
		except error.HTTPError as e:
			print(e, file=sys.stderr)
			posted = True
			sleeptime = 20

