#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Load and preprocess a corpus for idiom extraction'''

import os, time, json
import nltk.data
from bs4 import BeautifulSoup

def plain_text(corpus_file, no_split):
	'''Read in a plain text corpus, return a single document containing a list of unicode sentences.'''	

	splitter = nltk.data.load('tokenizers/punkt/english.pickle')
	# Read in corpus
	documents = []
	sentences = []
	with open(corpus_file, 'r') as f:
		for line in f:
			if line.strip():
				if no_split:
					sentences.append(unicode(line.strip(), 'utf-8'))
				else:
					sentences += splitter.tokenize(unicode(line.strip(), 'utf-8'))
	documents.append(sentences)
	
	return documents

def bnc(corpus_file, corpus_type, cache_path):
	'''
	Read in the British National Corpus (BNC) XML version, returns a list of documents.
	Documents are lists of dictionaries. Dictionaries contain unicode sentences and metadata 
	for offset annotation.	
	'''

	documents = []
	# Read parsed XML from cached file, for bnc/bnc-dev/bnc-test, if available
	if os.path.exists(cache_path):
		print 'Reading BNC from {0}'.format(cache_path)
		documents = json.load(open(cache_path, 'r'))
		return documents
		
	# Read BNC from file and parse, if no cached version available
	time_0 = time.time()
	print 'Processing BNC...'
	# Cycle through subdirectories
	subdirectories = sorted(os.listdir(corpus_file))
	for subdirectory in subdirectories:
		subdirectory_path = os.path.join(corpus_file, subdirectory)
		subsubdirectories = sorted(os.listdir(subdirectory_path))
		for subsubdirectory in subsubdirectories:
			subsubdirectory_path = os.path.join(subdirectory_path, subsubdirectory)
			document_ids = sorted(os.listdir(subsubdirectory_path))
			# Cycle through documents
			for document_id in document_ids:
				# Select only documents in development or test set of evaluation corpus
				if corpus_type in ['bnc-dev', 'bnc-test']:
					if corpus_type == 'bnc-dev':
						subset_documents = [u'CBC', u'CH1', u'A61', u'A18', u'ABC', u'ABV', u'A12', u'CBD', u'A1N', u'A19', u'A69', u'A75', u'AML', u'K2A', u'FU4', u'HD8', u'A60', u'AL7', u'A1F', u'A1D', u'A1L', u'A1H']
					else:
						subset_documents = [u'CBG', u'J1C', u'B03', u'A16', u'A6J', u'A15', u'A11', u'J1M', u'AP1', u'A5Y', u'G3H',  u'B2M', u'B0X', u'A6S', u'B1C', u'A10', u'H8W', u'A1E', u'A1G', u'GXL', u'A1M', u'K29', u'A63']
					if document_id[0:3] not in subset_documents:
						continue
				sentences_with_metadata = [] # Format: {'sentence': 'I win.', 'document_number': 'A00', 'sentence_number': '1'}
				document_path = os.path.join(subsubdirectory_path, document_id)
				parsed_xml = BeautifulSoup(open(document_path), 'lxml-xml')
				# Get metadata
				for idno in parsed_xml.find_all('idno'):
					if idno['type'] == 'bnc':
						document_idno = unicode(idno.string )
				for class_code in parsed_xml.find_all('classCode'):
					if class_code['scheme'] == 'DLEE':
						class_code = unicode(class_code.string)
						break
				# Cycle through sentences, extract unicode string
				for sentence in parsed_xml.find_all('s'):
					# Skip sentences containing gap elements
					if sentence.gap:
						continue
					sentence_number = unicode(sentence['n'])
					sentence_string = ''
					for descendant in sentence.descendants:
						if descendant.name in ['c', 'w']:
							sentence_string += unicode(descendant.string)
					# Store sentence with metadata
					sentence_with_metadata = {'document_id': document_idno, 'sentence_number': sentence_number, 'sentence': sentence_string}
					sentences_with_metadata.append(sentence_with_metadata)
				documents.append(sentences_with_metadata)
	print 'Done! Processing BNC took {0:.2f} seconds'.format(time.time() - time_0)
	
	# Cache parsed XML
	json.dump(documents, open(cache_path, 'w'))
	
	return documents
