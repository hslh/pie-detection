#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Get idioms from UsingEnglish.com, by scraping the a-z pages at www.usingenglish.com/reference/idioms/'''

import re, string
import requests
from bs4 import BeautifulSoup

def get_idioms(url, idioms_url):
	'''Scrape the idioms from the usingEnglish.com pages.'''

	idioms = []
	for letter in string.lowercase: # Cycle through categories 
		next_page = '{0}/{1}.html'.format(idioms_url, letter) # Page 1 of the category
		while next_page:
			# Get and parse page
			page = requests.get(next_page)
			soup = BeautifulSoup(page.content, 'html.parser')
			next_page = None
			for link in soup.find_all('a'):
				# Extract idiom from html
				if link.parent.name == 'dt':
					if ' ' in link.string: # Exclude single word 'idioms'
						idioms.append(link.string)
				# Get link to next page in the category
				elif link.parent.name == 'div':
						try:
							if link.parent['class'][0]	== 'pagination':
								if re.match('next', link.string):
									next_page = url + link['href']
						except KeyError: # Sometimes parent has no class
							pass

	return sorted(list(set(idioms)))
