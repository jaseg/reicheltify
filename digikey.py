#!/usr/bin/env python3

import argparse
from urllib import request,parse
from bs4 import BeautifulSoup as bs
from http.cookiejar import CookieJar
import string,sys,os,time
from os import path
try:
    import re2 as re
except ImportError:
    import re

parser = argparse.ArgumentParser(description='Throw text files at reichelt!')
parser.add_argument('tsvfile', nargs='?', default=sys.stdin, type=argparse.FileType('r'))
parser.add_argument('-s', '--sid', type=str, default=None, help='The session id of the digikey session')
args = parser.parse_args()
sid = args.sid

#Decipher input
items = []
total_items = 0
armed = False
for l in args.tsvfile:
	if not armed:
		if '# digikey' in l:
			armed = True
	else:
		if '# end' in l:
			break
		if not l.startswith('#'):
			qty, _, foo = l.partition('\t')
			part, _, cref = foo.partition('\t')
			qty, part, cref = int(qty.strip()), part.strip(), cref.strip()
			items.append((qty, part.strip(), cref))
			total_items += qty
print('Read ', len(items), ' items totalling ', total_items, 'parts')

cj = CookieJar()
op = request.build_opener(request.HTTPCookieProcessor(cj))
res = op.open('http://ordering.digikey.com/Ordering/FastAdd.aspx')
page = res.read()
pool = bs(page)
print('WebID:\t\t%s' % pool.find(id='ctl00_ctl00_mainContentPlaceHolder_lblWebID').text)
print('AccessID:\t%s' % pool.find(id='ctl00_ctl00_mainContentPlaceHolder_lblAccessID').text)

inputs = {}
for i in pool.find_all('input'):
	if 'name' in i.attrs:
		inputs[i['name']] = i.attrs.get('value', '')

def chunks(seq, size):
	return ((idx, seq[off:off+size]) for (idx, off) in enumerate(range(0, len(seq), size)))

for p,c in chunks(items, 20):
	for i,(qty, part, cref) in enumerate(c):
		inputs['ctl00$ctl00$mainContentPlaceHolder$mainContentPlaceHolder$txtQty'+str(i+1)] = qty
		inputs['ctl00$ctl00$mainContentPlaceHolder$mainContentPlaceHolder$txtPart'+str(i+1)] = part
		inputs['ctl00$ctl00$mainContentPlaceHolder$mainContentPlaceHolder$txtCref'+str(i+1)] = cref
	res = op.open('http://ordering.digikey.com/Ordering/FastAdd.aspx', data=parse.urlencode(inputs).encode('iso-8859-1'))
	page = res.read()
	pool = bs(page)
	errors = pool.find(id='ctl00_ctl00_mainContentPlaceHolder_mainContentPlaceHolder_gvAddPartError')
	if errors:
		for e in errors.find_all('tr')[1:]:
			qty = e.find(id='ctl00_ctl00_mainContentPlaceHolder_mainContentPlaceHolder_gvAddPartError_ctl02_txtErrorQuantity')['value']
			part = e.find(id='ctl00_ctl00_mainContentPlaceHolder_mainContentPlaceHolder_gvAddPartError_ctl02_txtErrorPartNumber')['value']
			cref = e.find(id='ctl00_ctl00_mainContentPlaceHolder_mainContentPlaceHolder_gvAddPartError_ctl02_txtErrorCustomerReference')['value']
			error = e.find(id='ctl00_ctl00_mainContentPlaceHolder_mainContentPlaceHolder_gvAddPartError_ctl02_lblErrorMessage').text
			print('Error:', error)
			print('\t%s\t%s\t%s' % (qty,part,cref))

