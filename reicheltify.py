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
import re
from decimal import Decimal
import requests

CHUNK_SIZE = 100 # How many items to post at once

parser = argparse.ArgumentParser(description='Throw text files at reichelt!')
parser.add_argument('csvfile', nargs='?', default=sys.stdin, type=argparse.FileType('r'))
parser.add_argument('-s', '--session', type=str, default=None, help='The session id of the reichelt session')
parser.add_argument('--clear-cart', action='store_true', help='First clear the shopping cart')
args = parser.parse_args()

cart = lambda session, la='0': 'http://www.reichelt.de/Warenkorb/5/index.html?ACTION=5&LA='+la+'&SID='+session
de_en_float = lambda s: s.replace('.', '').replace(',', '.')

session = args.session
if not session:
	print('No session ID given.')
	exit(1)

def post_items(items, session):
	#itemid needs to be encoded in iso-8859-1/latin-1 because that's what reichelt uses
	# ('Anzahl_Unknown[%d]' % i, count) for i, (count, _) in enumerate(items), 
	rd = {}
	for i, (count, itemid) in enumerate(items):
		rd['Anzahl_Unknown[%d]' % i] = count
		rd['Input_Unknown[%d]' % i] = itemid.encode('iso-8859-1')
	rq = request.Request('http://www.reichelt.de/index.html?;ACTION=19;LA=5012;SID={}'.format(args.session), data=parse.urlencode(rd).encode('iso-8859-1'))
	res = request.urlopen(rq)
	page = res.read()
	pool = bs(page, 'lxml')
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
	for el in pool.find_all('p', {'style': 'color: red; font-size: 10px;'}):
		print('Item unavailable:', el.parent.parent.parent.find_all('a')[1].text)

def basketcost(session):
	pool = bs(requests.get(cart(session)).text, 'lxml')
	return Decimal(de_en_float(pool.find(id='basketsum').text))

def add_to_cart(items, session, old_cost=Decimal(0), old_total_items=0, old_total_parts=0):
	part_count     = sum(int(count) for count,_ in items)

	for i in range(0, len(items), CHUNK_SIZE):
		post_items(items[i:i+CHUNK_SIZE], session)

	new_cost       = basketcost(session)
	print('{}: Posted {} items totalling {} parts at {:.2f}€'.format(section, len(items), part_count, new_cost-old_cost))

	return new_cost, old_total_items+len(items), old_total_parts+part_count

def clear_cart(session):
	requests.post(cart(session, la='5'), data={'Delete[_all_]': 'WK+löschen'})


if args.clear_cart:
	print('Clearing shopping cart')
	clear_cart(session)


#Decipher input
items, section = [], None
old_cost, total_items, total_parts = basketcost(session), Decimal(0), Decimal(0)
original_cost = old_cost

for lineno_minus_one,l in enumerate(args.csvfile):
	if l.startswith('!'):
		if 'END' in l:
			break

		if items:
			old_cost, total_items, total_parts = add_to_cart(items, session, old_cost, total_items, total_parts)
		elif section:
			print('Empty section:', section)
		section, items = l[1:].strip(), []
	elif l.strip() and not l.startswith('#'):
		try:
			count, itemid, *_ = l.split('\t')[:2]
			items.append((count, itemid.strip()))
		except:
			print('Line {}: Invalid syntax. Expected at least count and item ID, tab-separated.'.format(lineno_minus_one+1))

old_cost, total_items, total_parts = add_to_cart(items, session, old_cost, total_items, total_parts)

print('Posted a total of', total_items, 'items, totalling', total_parts, 'parts.')
print("Total cart cost is {:.2f}€, this list's cost is {:.2f}€.".format(old_cost, old_cost-original_cost))
print('URL to shopping cart: {}'.format(cart(session)))

