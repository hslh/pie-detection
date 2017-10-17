#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Get information from Wiktionary using the MediaWiki API and process returned content.'''

import re
import requests
import lxml.html

def get_category_members(category):
	'''
	Use the MediaWiki API to get all category members of a Wiktionary category. 
	Takes a category name. Returns a list of pagetitles.
	'''

	titles = []
	cont = True
	cmcontinue = '' # Continuation point for query
	# Get titles until no members left
	while(cont):
		# Construct query
		endpoint = 'https://en.wiktionary.org/w/api.php?' # Wiktionary API endpoint
		action = 'action=' + 'query' # Which action to take (query, naturally)
		format = 'format=' + 'json' # Output format
		lists = 'list=' + 'categorymembers'
		cmtitle = 'cmtitle=Category:' + category
		cmtitle = re.sub(' ', '%20', cmtitle)
		cmlimit = 'cmlimit=' + '500' # Query result limit
		cmprop = 'cmprop=' + 'title' # Get page titles only
		
		query = endpoint + '&'.join([action, format, lists, cmtitle, cmprop, cmlimit])
		if cmcontinue: # Adding cmcontinue to query makes sure it continues from end of previous query
			query += '&cmcontinue=' + cmcontinue

		# Get and process results
		res_raw = requests.get(query)
		res_json = res_raw.json()
		# Collect page titles, i.e. idioms 
		category_members = res_json['query']['categorymembers']
		for category_member in category_members:
			title = category_member['title']
			if re.search('(^Appendix:)|(^Category:)|(^Special:)|(^Wiktionary:)|(^Category_talk:)|(^Citations:)', title): # Filter out special pages 
				print "Filtered out '{0}' from idiom list".format(title)
			elif ' ' in title: # Exclude single-word 'idioms'
				titles.append(title.strip())
		# Check for more members in category
		try:
			cmcontinue = res_json['continue']['cmcontinue']
			cont = True
		except KeyError:
			cont = False

	return sorted(list(set(titles)))

def get_page(title):
	'''
	Use the MediaWiki API to get *** from a Wiktionary page.
	Takes a page title. Returns ***
	'''
	
	# Construct query
	endpoint = 'http://en.wiktionary.org/w/api.php?' # Wiktionary API endpoint
	action = 'action=' + 'query' # Which action to take (query, naturally)
	format = 'format=' + 'json' # Output format
	prop = 'prop=' + 'revisions' # What info to get
	rvprop = 'rvprop=' + 'content'
	rvparse = 'rvparse' # Parse content into html
	titles = 'titles=' + title
	titles = re.sub(' ', '%20', titles)
	query = endpoint + '&'.join([action, format, prop, rvprop, rvparse, titles])

	# Process result, get html only
	try:
		res_raw = requests.get(query)
		res_json = res_raw.json()
		temp_1 = res_json['query']['pages'] # Dig through first two layers
		res_html = temp_1[temp_1.keys()[0]]['revisions'][0]['*'] # Dig through remaining four layers
		parsed_html = lxml.html.document_fromstring(res_html)
	except KeyError:
		return
		
	return parsed_html
