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
"""Mass-order stuff from digikey

This script places a tab-separated list of parts (format [quantity]\t+[part number]\t+[comment]) in a digikey shopping cart. It outputs a list of any problems digikey reports (including the corresponding input lines) on stderr and outputs the digikey Web ID and Access ID on stdout. You may use the Web and Access IDs to open the shopping cart the script creates with the "resume order" page to be found via the button on the bottom of the shopping cart page.

Currently it is not possible to tell the script a shopping cat to which to add the items.
"""

parser = argparse.ArgumentParser(description='Throw text files at reichelt!')
parser.add_argument('tsvfile', nargs='?', default=sys.stdin, type=argparse.FileType('r'))
args = parser.parse_args()

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

#Get a digikey session. Digikey uses some rather arcane magic to track sessions, I would *really* like to know what the __VIEWSTATE variable contains.
cj = CookieJar()
op = request.build_opener(request.HTTPCookieProcessor(cj))
res = op.open('http://ordering.digikey.com/Ordering/FastAdd.aspx')
page = res.read()
pool = bs(page)
print('WebID:\t\t%s' % pool.find(id='ctl00_ctl00_mainContentPlaceHolder_lblWebID').text)
print('AccessID:\t%s' % pool.find(id='ctl00_ctl00_mainContentPlaceHolder_lblAccessID').text)

#Find all form fields to be posted to the server
inputs = {}
for i in pool.find_all('input'):
	if 'name' in i.attrs:
		inputs[i['name']] = i.attrs.get('value', '')

#Helper function
def chunks(seq, size):
	return ((idx, seq[off:off+size]) for (idx, off) in enumerate(range(0, len(seq), size)))

#Post data in 20-item chunks because that is what digikey does
#TODO: try more ;)
for p,c in chunks(items, 20):
	#Construct the item list
	for i,(qty, part, cref) in enumerate(c + [('', '', '')]*(20-len(c))): #pad the list to 20 entries
		inputs['ctl00$ctl00$mainContentPlaceHolder$mainContentPlaceHolder$txtQty'+str(i+1)] = qty
		inputs['ctl00$ctl00$mainContentPlaceHolder$mainContentPlaceHolder$txtPart'+str(i+1)] = part
		inputs['ctl00$ctl00$mainContentPlaceHolder$mainContentPlaceHolder$txtCref'+str(i+1)] = cref
	#Post the data
	res = op.open('http://ordering.digikey.com/Ordering/FastAdd.aspx', data=parse.urlencode(inputs).encode('iso-8859-1'))
	page = res.read()
	pool = bs(page)
	#Parse and output any errors (invalid input, part not found etc.) digikey reports
	errors = pool.find(id='ctl00_ctl00_mainContentPlaceHolder_mainContentPlaceHolder_gvAddPartError')
	if errors:
		for e in errors.find_all('tr')[1:]:
			qty = e.find(id='ctl00_ctl00_mainContentPlaceHolder_mainContentPlaceHolder_gvAddPartError_ctl02_txtErrorQuantity')['value']
			part = e.find(id='ctl00_ctl00_mainContentPlaceHolder_mainContentPlaceHolder_gvAddPartError_ctl02_txtErrorPartNumber')['value']
			cref = e.find(id='ctl00_ctl00_mainContentPlaceHolder_mainContentPlaceHolder_gvAddPartError_ctl02_txtErrorCustomerReference')['value']
			error = e.find(id='ctl00_ctl00_mainContentPlaceHolder_mainContentPlaceHolder_gvAddPartError_ctl02_lblErrorMessage').text
			print('Error:', error, file=sys.stderr)
			print('\t%s\t%s\t%s' % (qty,part,cref), file=sys.stderr)

