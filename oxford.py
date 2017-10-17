#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Get idioms from the online Oxford Dictionary of English Idioms, by scraping the pages at www.oxfordreference.com.
Refines the idioms by removing duplicates, and expanding things in parentheses, dealing with special cases. 
'''

import re, requests, itertools
from bs4 import BeautifulSoup

def get_idioms(url, landing_url, use_socks_proxy = False):
	'''
	Scrapes idioms from the ODEI website, gets 100 entries per page, 
	navigates to entry page, gets idiom, cycles through pages
	'''
	idioms = []
	# Set proxy, if applicable, requires pysocks to be installed
	if use_socks_proxy:
		proxies = {'http': "socks5://127.0.0.1:8080"}
	else:
		proxies = {}
	# Get and parse first page
	page = requests.get(landing_url)
	soup = BeautifulSoup(page.content, 'html.parser')
	# Scrape pagination information
	links = soup.find_all('a')
	for link in links:
		if link.parent.name == 'div':
			try:
				if link.parent['class'][0] == 't-data-grid-pager':
					last_page = link.text # Number of pages to cycle through
					url_template = link['href']
			except KeyError:
				pass # Sometimes parent has no class
	# Cycle through pages, get actual idioms
	for i in range(1, int(last_page) + 1):
		print 'Scraping page {0} of {1}'.format(i, last_page) # Very slow, so give progress updates
		# Get next page url
		if i < int(last_page):
			next_page = url + re.sub('gridpager/{0}'.format(last_page), 'gridpager/{0}'.format(i + 1), url_template)
		# Find links to pages containing idioms
		links = soup.find_all('a')
		for link in links:
			if link.parent.name == 'h2':
				try:
					if link.parent['class'][0] == 'itemTitle':
						# Get page with idiom entries
						entry_page = requests.get(url + link['href'], proxies=proxies)
						entry_soup = BeautifulSoup(entry_page.content, 'html.parser')
						# Extract idiom
						for idiom in entry_soup.find_all('em'):
							try:
								if idiom.parent.parent['class'][0] == 'div1':
									if ' ' in idiom.text: # Filter out single word 'idioms'
										idioms.append(idiom.text) # Store the actual idiom 
							except KeyError:
								pass # Sometimes grandparent has no class
				except KeyError:
					pass # Sometimes parent has no class
		# Get and parse next page
		page = requests.get(next_page)
		soup = BeautifulSoup(page.content, 'html.parser')

	return sorted(list(set(idioms)))

def refine_idioms(idioms):
	'''
	Oxford scraping output is messy. Removes duplicates containing ':'. 
	Expands optionals in parentheses. Deals with some exceptional cases individually
	'''

	refined_idioms = []
	for idiom in idioms:
		# Fix scraping errors
		if idiom == 'like (or as if) it is going out of fashion (or style':
			idiom += ')'
		if idiom == 'cog in the wheel (or machine':
			idiom += ')'
		if idiom == 'get you (him, her':
			idiom += ', etc.)!'
		has_parentheses = False
		if idiom[-1] != ':': # All duplicates end in ':' 
			# Get all parenthesis pairs + content
			if re.findall('\(.*\)', idiom):
				pairs_of_parentheses = re.finditer('\(.*?\)', idiom)
				# Cycle through pairs of parentheses, collect parts of idiom, and their expansions/variations
				idiom_parts = []
				previous_end = 0
				for pair_of_parentheses in pairs_of_parentheses:
					starts_with_also = False # e.g. (also sure as fate)
					starts_with_or = False # e.g. (or get something off the ground)
					or_in_middle = False # e.g. (final or last)
					contains_etc = False # e.g. (me, him, etc.)
					# Get indices
					start = pair_of_parentheses.start()
					end = pair_of_parentheses.end()
					# Examine content between parentheses - set conditions
					content_between_parentheses = pair_of_parentheses.group(0)[1:-1] # Get content without ()
					if re.match('also\\b', content_between_parentheses):
						starts_with_also = True
					if re.match('or\\b', content_between_parentheses):
						starts_with_or = True
					if re.search('.\\bor\\b', content_between_parentheses):
						or_in_middle = True
					if re.search('etc\.', content_between_parentheses):
						contains_etc = True
					# Add the non-parenthesized bit before the current pair of parentheses (if it exists)
					idiom_part_before = idiom[previous_end:start]
					if idiom_part_before:
						idiom_parts.append([idiom_part_before])
					## Deal with different types of content between parentheses
					# Deal with the case with the '/', which occurs in exactly 1 idiom entry
					if content_between_parentheses == 'or get your fingers burned/burnt':
						content_between_parentheses = 'or get your fingers burned or get your fingers burnt'
						or_in_middle = True
					# Deal with some especially difficult parentheses cases first, individually
					if '(' in content_between_parentheses:
						if content_between_parentheses == 'or bring someone back (down':
							refined_idioms.append(u'bring someone back to earth')
							refined_idioms.append(u'bring someone back down to earth')
							end = len(idiom)
						if content_between_parentheses == 'or give someone pause (for thought':
							refined_idioms.append(u'give someone pause')
							refined_idioms.append(u'give someone pause for thought')
							end = len(idiom)
						if content_between_parentheses == 'or herein (or therein':
							idiom_parts[-1].append(u'herein lies')
							idiom_parts[-1].append(u'therein lies')
							idiom_parts.append([u'a tale'])
							end = len(idiom)
					# Simplest case, just generate idiom with parentheses removed, keeping content in parentheses
					# EXAMPLE: (all) at sea -> all at sea, at sea
					elif not starts_with_also and not starts_with_or and not or_in_middle and not contains_etc:
						idiom_part_between_parentheses = ['', content_between_parentheses]
						idiom_parts.append(idiom_part_between_parentheses)
					# Simplest'case starting with 'or'. Generate idiom with n words before parentheses replaced by the n words in the parentheses
					# EXAMPLE: I should cocoa (or coco) -> I should cocoa, I should coco
					elif not starts_with_also and starts_with_or and not or_in_middle and not contains_etc:
						num_words_to_replace = len(content_between_parentheses.split(' ')) - 1 # -1 because of or
						content_between_parentheses_without_or = ' '.join(content_between_parentheses.split(' ')[1:])
						idiom_part_before_split = idiom_part_before.strip().split(' ')
						idiom_part_before_trimmed = ' '.join(idiom_part_before_split[:-num_words_to_replace])
						idiom_part_before_variant = idiom_part_before_trimmed + ' ' + content_between_parentheses_without_or
						if idiom_part_before[0] == ' ': # Add initial space if it got removed incidentally
							idiom_part_before_variant = ' ' + idiom_part_before_variant						
						idiom_parts[-1].append(idiom_part_before_variant) # Add as variant to previous part
					# Simplest case with or in the middle. Generate idioms for each part separated by 'or'.
					# EXAMPLE: a (final or last) turn of the screw -> a final turn of the screw, a last turn of the screw
					elif not starts_with_also and not starts_with_or and or_in_middle and not contains_etc:
						content_parts = content_between_parentheses.split(' or ')
						idiom_parts.append(content_parts)
					# Case with both or at the start and in the middle. Generate idioms with replacement for each part separated by 'or'
					# EXAMPLE: a bad (or bitter or nasty) taste -> a bad taste, a bitter taste, a nasty taste
					elif not starts_with_also and starts_with_or and or_in_middle and not contains_etc:
						content_parts = content_between_parentheses[3:].split(' or ') # Strip initial 'or' and split in parts
						idiom_part_before_split = idiom_part_before.strip().split(' ')
						for content_part in content_parts:
							num_words_to_replace = len(content_part.split(' '))
							idiom_part_before_trimmed = ' '.join(idiom_part_before_split[:-num_words_to_replace])
							idiom_part_before_variant = idiom_part_before_trimmed + ' ' + content_part
							idiom_parts[-1].append(idiom_part_before_variant)
					# Case with 'also' at the start, signals full replacement, only two cases, one also with 'or'
					# 1. sure as eggs is eggs (also sure as fate) 2. left, right, and centre (also left and right or right and left)
					elif starts_with_also and not contains_etc:
						if not or_in_middle:
							idiom_part_before_variant = content_between_parentheses[5:] # Remove 'also'
							idiom_parts[-1].append(idiom_part_before_variant)
						else:
							idiom_part_before_variants = content_between_parentheses[5:].split(' or ')
							idiom_parts[-1] += idiom_part_before_variants
					# Cases with etc. are rare, and require individual treatment
					elif contains_etc:
						if content_between_parentheses in ['me, him, etc.', 'him, her, etc.']:
							expanded_series = ['me', 'you', 'him', 'her', 'us', 'them', 'it']
							idiom_parts.append(expanded_series)
						elif content_between_parentheses == 'or tell, etc.':
							idiom_part_before_variant = 'tell'
							idiom_parts[-1].append(idiom_part_before_variant)
						elif content_between_parentheses == 'or herself, etc.':
							idiom_part_before_trimmed = ' '.join(idiom_part_before.split()[:-1])
							variant_series = ['myself', 'yourself', 'herself', 'itself', 'ourselves', 'yourselves', 'themselves']
							for variant in variant_series:
								idiom_part_before_variant = idiom_part_before_trimmed + ' ' + variant
								idiom_parts[-1].append(idiom_part_before_variant)
						elif content_between_parentheses == 'or bore etc.':
							idiom_part_before_variant = 'bore'
							idiom_parts[-1].append(idiom_part_before_variant)	
						elif content_between_parentheses == 'or your etc.':
							idiom_part_before_trimmed = ' '.join(idiom_part_before.split()[:-1])
							variant_series = ['my', 'your', 'his', 'her', 'its', 'our', 'your', 'their']
							for variant in variant_series:
								idiom_part_before_variant = idiom_part_before_trimmed + ' ' + variant
								idiom_parts[-1].append(idiom_part_before_variant)				
						elif content_between_parentheses in ['or you or him, etc.', 'or her, him, etc.']:
							idiom_part_before_trimmed = ' '.join(idiom_part_before.split()[:-1])
							variant_series = ['you', 'him', 'her', 'us', 'them', 'it']
							for variant in variant_series:
								idiom_part_before_variant = idiom_part_before_trimmed + ' ' + variant
								idiom_parts[-1].append(idiom_part_before_variant)		
						elif content_between_parentheses == 'or forty-something, etc.':
							idiom_parts = [] # Single-word idiom, ignore
					previous_end = end
				# Add remaining part of idiom after final pair of parentheses
				idiom_parts.append([idiom[end:]])
				# From the collected idiom parts and variations, generate all idiom variations and add them to the list
				for refined_idiom in itertools.product(*idiom_parts):
					refined_idiom = ''.join(refined_idiom)
					refined_idiom = re.sub(' +', ' ', refined_idiom) # Remove double spaces
					refined_idiom = re.sub('(^ )|( $)', '', refined_idiom) # Remove initial spaces and final spaces
					if len(refined_idiom.split(' ')) > 1: # Remove single-word idioms, e.g. 'forty-something' (or thirty-something')
						refined_idioms.append(refined_idiom)
			else:
				refined_idioms.append(idiom)
	return refined_idioms
