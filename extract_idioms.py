#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Extract potential idiomatic expressions from a corpus, based on idioms from a dictionary.'''

import config
import process_corpus
import wiktionary
import using_english
import oxford
import utils
from utils import u8

import re, os, json, random, time

def combine_sets(combination_type, a, b, c = []):
	'''Combines 2/3 sets of idioms in different ways'''
	if combination_type == 'intersection':
		if c:
			return list(set(a) & set(b) & set(c))
		else:
			return list(set(a) & set(b))
	elif combination_type == '2of3':
		return list((set(a) & set(b)) | (set(b) & set(c)) | (set(a) & set(c)))
	elif combination_type == 'union':
		if c:
			return list(set(a) | set(b) | set(c))
		else:
			return list(set(a) | set(b))

def get_idiom_list(dictionary_type = config.DICT, case_sensitive = False):
	'''Gets idiom list, either from file or via API'''

	# Read in dictionary type
	if len(dictionary_type) == 1:
		dictionary_type = dictionary_type[0]
	elif len(dictionary_type) != 2:
		raise ValueError('No valid dictionary specified!')

	# Single dictionaries
	if dictionary_type in ['wiktionary', 'ue', 'oxford']:
		# Try to find the most recent cached idiom list
		ifn = ''
		ifn_pattern = 'idiom_list_{0}_[0-9\-]+\.json$'.format(dictionary_type)
		for candidate_ifn in sorted(os.listdir(config.WORK_DIR), reverse = True):
			if re.match(ifn_pattern, candidate_ifn):
				ifn = os.path.join(config.WORK_DIR, candidate_ifn)
				break
		# Don't use the cached list, but scrape a new one
		if not os.path.isfile(ifn) or config.NO_CACHE:
			if dictionary_type == 'wiktionary':
				idioms = wiktionary.get_category_members(category = 'English idioms')
			if dictionary_type == 'ue':
				idioms = using_english.get_idioms(config.UE_URL, config.UE_IDOMS_URL)
			if dictionary_type == 'oxford':
				idioms = oxford.get_idioms(config.OX_URL, config.OX_LANDING_URL)
			# Cache idiom list
			ofn = '{0}/idiom_list_{1}_{2}.json'.format(config.WORK_DIR, dictionary_type, config.TIME)
			with open(ofn, 'w') as of:
				json.dump(idioms, of)
		# Read idiom list from file
		else:
			print 'Reading idiom list from {0}'.format(ifn)
			with open(ifn, 'r') as f:
				idioms = json.load(f)
		# Refine Oxford idiom list
		if dictionary_type == 'oxford':
			idioms = oxford.refine_idioms(idioms)
		# Lower-case everything if we ignore case
		if not case_sensitive:
			idioms = [idiom.lower() for idiom in idioms]

	# Combinations of all dictionaries
	elif dictionary_type in ['intersection', 'union', '2of3']:
		# Get single dictionaries first
		wiktionary_idioms = get_idiom_list(dictionary_type = ['wiktionary'], case_sensitive = case_sensitive)
		ue_idioms = get_idiom_list(dictionary_type = ['ue'], case_sensitive = case_sensitive)
		oxford_idioms = get_idiom_list(dictionary_type = ['oxford'], case_sensitive = case_sensitive)
		# Combine dictionaries
		if not case_sensitive: 
			idioms = combine_sets(dictionary_type, wiktionary_idioms, ue_idioms, oxford_idioms)
		# Keep case where possible, lower-case where dictionaries conflict
		else:
			idioms = combine_sets(dictionary_type, wiktionary_idioms, ue_idioms, oxford_idioms)
			idioms_lower = [idiom.lower() for idiom in idioms]
			# Lower-case first letter which is always upper-case in UE
			ue_fixed = [idiom[0].lower() + idiom[1:] for idiom in ue_idioms]
			additional_idioms = combine_sets(dictionary_type, wiktionary_idioms, ue_fixed, oxford_idioms)
			for additional_idiom in additional_idioms:
				if additional_idiom.lower() not in idioms_lower:
					idioms.append(additional_idiom)
					idioms_lower.append(additional_idiom.lower())
			# Add all idioms which have case differences in other places
			wiktionary_lower = [idiom.lower() for idiom in wiktionary_idioms]
			ue_lower = [idiom.lower() for idiom in ue_idioms]
			oxford_lower = [idiom.lower() for idiom in oxford_idioms]
			additional_idioms = combine_sets(dictionary_type, wiktionary_lower, ue_lower, oxford_lower)
			for additional_idiom in additional_idioms:
				if additional_idiom.lower() not in idioms_lower:
					idioms.append(additional_idiom)

	# Combination of a pair of dictionaries
	elif len(dictionary_type) == 2:
		print 'Taking the intersection of a pair of dictionaries'
		dictionary_idioms_1 = get_idiom_list(dictionary_type = dictionary_type[0:1], case_sensitive = case_sensitive)
		dictionary_idioms_2 = get_idiom_list(dictionary_type = dictionary_type[1:2], case_sensitive = case_sensitive)
		# Combine dictionaries
		if not case_sensitive:
			idioms = combine_sets('intersection', dictionary_idioms_1, dictionary_idioms_2)
		# Keep case where possible, lower-case where dictionaries conflict
		else: 
			idioms = combine_sets('intersection', dictionary_idioms_1, dictionary_idioms_2)
			idioms_lower = [idiom.lower() for idiom in idioms]
			# Lower-case first letter which is always upper-case in UE
			additional_idioms = []
			if dictionary_type[0:1] == 'ue':
				ue_fixed = [idiom[0].lower() + idiom[1:] for idiom in dictionary_idioms_1]
				additional_idioms = combine_sets('intersection', dictionary_idioms_2, ue_fixed)
			elif dictionary_type[1:2] == 'ue':
				ue_fixed = [idiom[0].lower() + idiom[1:] for idiom in dictionary_idioms_2]
				additional_idioms = combine_sets('intersection', dictionary_idioms_1, ue_fixed)
			if additional_idioms:
				for additional_idiom in additional_idioms:
					if additional_idiom.lower() not in idioms_lower:
						idioms.append(additional_idiom)
						idioms_lower.append(additional_idiom.lower())
			# Add all idioms which have case differences in other places
			dictionary_idioms_1_lower = [idiom.lower() for idiom in dictionary_idioms_1]
			dictionary_idioms_2_lower = [idiom.lower() for idiom in dictionary_idioms_2]
			additional_idioms = combine_sets('intersection', dictionary_idioms_1_lower, dictionary_idioms_2_lower)
			for additional_idiom in additional_idioms:
				if additional_idiom.lower() not in idioms_lower:
					idioms.append(additional_idiom)

	return idioms

def string_match(idioms, documents, case_sensitive = False, expand_pronouns = True, fuzzy = False, inflect = False):
	'''
	Extracts idioms by exact, fuzzy, or inflectional string matching.
	Expands idioms containing indefinite pronouns and deals with idioms
	containing em-dash wildcards. Maps all matched idioms back to their
	dictionary form and extracts context around the idiom.	
	'''

	# Set flags
	if case_sensitive:
		flags = 0
	else:
		flags = re.I

	# Inter-word separator for regex: word boundaries + optional intervening words
	separator = r'\b\W+(?:\w+\W+){0,' + str(config.INT_WORDS) + r'}\b'

	# Expand indefinite pronouns in idioms (e.g. 'someone')
	if expand_pronouns:
		idioms, expanded_form_map = utils.expand_indefinite_pronouns(idioms)

	# Get all inflectional variants of idioms
	if inflect:
		idioms, inflected_form_map = utils.inflect_idioms(idioms, config.MORPH_DIR)

	extracted_idioms = [] # List of dicts, format: {'snippet': "", 'idiom': "", 'start': 0, 'end': 0, 'bnc_doc_id': "", 'bnc_sent': "", 'bnc_char_start': 0, 'bnc_char_end': 0}

	# Generate regular expression matching all idioms
	idiom_regex = ''
	for idiom in idioms:
		idiom_words = idiom.split(' ')
		# Fuzzy matching: add optional 1/2/3-character suffix to each idiom word 
		if fuzzy:
			idiom_words = [re.escape(iw) + '\w?' * 3 for iw in idiom_words] # Escape special chars, add fuzzy suffix, add boundaries
		# Regular string matching
		else:
			idiom_words = [re.escape(iw) for iw in idiom_words] # Escape special chars
		idiom_regex = idiom_regex + r'\b' + separator.join(idiom_words) + r'\b'
		if idiom != idioms[-1]:
			idiom_regex += '|'
			
		# Replace all em-dashes by a wildcard (\w+)
		idiom_regex = re.sub(u'\\\—', r'\w+', idiom_regex)

	# Do actual extraction
	tokenizer = utils.load_tokenizer()
	for sentences in documents:
		# Get sentence strings from BNC data
		if config.CORPUS_TYPE[0:3] == 'bnc':
			sentences_with_metadata = sentences
			sentences = [sentence_with_metadata['sentence'] for sentence_with_metadata in sentences_with_metadata]
		# Cycle through sentences in document
		for idx, sentence in enumerate(sentences):
			matches = re.finditer(idiom_regex, sentence, flags = flags)
			tokenized_sentence = ''
			for match in matches:
				# Only tokenize once, and only when a match is found
				if not tokenized_sentence:
					tokenized_sentence = utils.tokenize(tokenizer, sentence)
				# Get token offsets from match offsets
				for token in tokenized_sentence:
					if token.idx == match.start():
						first_idiom_token_i = token.i
					if token.idx + len(token.text) == match.end():
						last_idiom_token_i = token.i
						break
				# Get BNC metadata/set dummy values
				if config.CORPUS_TYPE[0:3] == 'bnc':
					bnc_document_id = sentences_with_metadata[idx]['document_id']
					bnc_sentence = sentences_with_metadata[idx]['sentence_number']
					bnc_char_start = match.start()
					bnc_char_end = match.end()
				else:
					bnc_document_id = '-'
					bnc_sentence = '-'
					bnc_char_start = 0
					bnc_char_end = 0
				# Get n-word context
				if config.CONTEXT_TYPE == 'w':
					# Get snippet
					snippet_start = max(0, first_idiom_token_i - config.CONTEXT_NUMBER)
					snippet_end = min(len(tokenized_sentence), last_idiom_token_i + 1 + config.CONTEXT_NUMBER)
					snippet = tokenized_sentence[snippet_start:snippet_end].text
					# Get idiom character offsets in snippet
					char_offset_span = tokenized_sentence[snippet_start].idx
					char_offset_start = match.start() - char_offset_span
					char_offset_end = match.end() - char_offset_span
				# Get n-sentence context
				elif config.CONTEXT_TYPE == 's':
					if config.CONTEXT_NUMBER == 0:
						snippet = sentence
						char_offset_start = match.start()
						char_offset_end = match.end()
					else:
						# Get surrounding sentences to form snippet
						first_snippet_sentence_idx = max(0, idx - config.CONTEXT_NUMBER)
						last_snippet_sentence_idx = min(len(sentences), idx + 1 + config.CONTEXT_NUMBER)
						snippet_sentences = sentences[first_snippet_sentence_idx:last_snippet_sentence_idx]
						snippet = ' '.join(snippet_sentences)
						# Adjust offset for length of preceding sentences and joining space to the current sentence
						num_preceding_sentences = idx - first_snippet_sentence_idx
						char_offset_span = len(' '.join(snippet_sentences[:num_preceding_sentences]))
						char_offset_start = match.start() + char_offset_span + 1
						char_offset_end = match.end() + char_offset_span + 1
						
				# Get dictionary form of idiom
				matched_string = sentence[match.start():match.end()]
				if not case_sensitive:
					matched_string = matched_string.lower()
				dictionary_form = ''
				# Deal with em-dash wildcard idiom, and idioms matched with non-spaces
				if matched_string not in idioms:
					for idiom in idioms:
						idiom_words = idiom.split(' ')
						if fuzzy:
							idiom_words = [re.escape(idiom_word) + '\w?' * 3 for idiom_word in idiom_words]
						else:
							idiom_words = [re.escape(idiom_word) for idiom_word in idiom_words]
						single_idiom_regex = r'\b' + separator.join(idiom_words) + r'\b'
						if u'\u2014' in idiom:
							single_idiom_regex = re.sub(ur'\\\u2014', r'\w+', single_idiom_regex)
						if re.match(single_idiom_regex, matched_string):
							dictionary_form = idiom
							break
				# Occurs exactly in idiom list, so already is dictionary form 
				else:
					dictionary_form = matched_string
				# Map expanded and/or inflected idioms back to base form
				if inflect:
					dictionary_form = inflected_form_map[dictionary_form]
				if expand_pronouns:
					dictionary_form = expanded_form_map[dictionary_form]

				extracted_idioms.append({'snippet': snippet, 'idiom': dictionary_form, 'start': char_offset_start, 
					'end': char_offset_end, 'bnc_document_id': bnc_document_id, 'bnc_sentence': bnc_sentence, 
					'bnc_char_start': bnc_char_start, 'bnc_char_end': bnc_char_end})

	return extracted_idioms

def parse_extract(idioms, sentences):
	'''
	Extracts idioms based on the dependency parse of the idiom and sentence.
	Parse all idioms, optionally in context, get their parse trees and top node 
	lemmata. Then, parse each sentence, check if the top node lemma is present,
	and match the idiom parse tree to a subtree of the sentence parse. Deal 
	with idioms containing indefinite pronouns and em-dashes properly.
	'''

	parser = utils.load_parser(config.PARSER)
	extracted_idioms = [] # List of dicts, format: {'snippet': "", 'idiom': "", 'start': 0, 'end': 0, 'bnc_doc_id': "", 'bnc_sent': "", 'bnc_char_start': 0, 'bnc_char_end': 0}
	# Use a PoS-ambiguous word to parse idioms containing em-dash wildcards
	ambiguous_word = 'fine'

	# Parse idioms in context
	if config.SENTENCES:
		cache_file = '{0}/example_sentences_{1}_{2}_{3}.json'.format(config.WORK_DIR, '_'.join(config.DICT), config.SENTENCES.split('/')[-1][:-4], config.TIME)
		idioms_with_sentences = utils.get_example_sentences(idioms, config.SENTENCES, cache_file)
		parsed_idioms = utils.parse_example_sentences(idioms_with_sentences, ambiguous_word, parser)
	# Parse idioms without context
	else:
		parsed_idioms = []
		for idiom in idioms:
			parsed_idioms.append(utils.parse_idiom(idiom, ambiguous_word, parser))

	# Extract idiom instances by matching parse trees
	for sentences in documents:
		time_0 = time.time()
		print 'Parsing document...'
		# Get sentence strings from BNC data and parse
		if config.CORPUS_TYPE [0:3]== 'bnc':
			sentences_with_metadata = sentences
			sentences = [sentence_with_metadata['sentence'] for sentence_with_metadata in sentences_with_metadata]
			# Parse sentence, and turn resulting Doc into Span object
			parsed_sentences = [utils.parse(parser, sentence)[:] for sentence in sentences]
		# Parse corpus as a whole, let Spacy do the sentence splitting
		else:
			parsed_corpus = utils.parse(parser, ' '.join(sentences))
			parsed_sentences = parsed_corpus.sents

		print 'Done! Parsing document took {0:.2f} seconds'.format(time.time() - time_0)
		# Cycle through sentences, attempt to match parse trees
		for sentence_idx, parsed_sentence in enumerate(parsed_sentences):
			for parsed_idiom in parsed_idioms:

				# Get idiom information
				idiom_top_lemma = parsed_idiom[0]
				idiom_top_token = parsed_idiom[1]
				idiom_subtree = parsed_idiom[2]
				# If not parsed in context, there is no stored list, so get generator
				if not idiom_subtree: 
					idiom_subtree = idiom_top_token.subtree
				# Use list, rather than generator
				idiom_subtree = [x for x in idiom_subtree]
				has_em_dash = parsed_idiom[3]
				# Save previously matched indices to check for overlapping spans
				previously_matched_indices = [] 

				# When idiom top lemma is em-dash, check if other lemma-tokens occur in sentence, only then try matching the parse trees
				consider_this_em_dash_idiom = False
				if has_em_dash and idiom_top_lemma == ambiguous_word:
					idiom_content_tokens = [token for token in idiom_subtree if token.tag_ not in ['DT'] and token != idiom_top_token]
					sentence_lemmata = [token.lemma_ for token in parsed_sentence]
					if all([idiom_content_token.lemma_ in sentence_lemmata for idiom_content_token in idiom_content_tokens]):
						consider_this_em_dash_idiom = True

				# Cycle through sentence parse, match top lemma to sentence lemma and idiom parse tree to sentence parse tree
				for sentence_token in parsed_sentence:
					# Match top lemma or em-dash heuristic or match any idiom token as possible top token in case of no directionality
					if sentence_token.lemma_ == idiom_top_token.lemma_ or consider_this_em_dash_idiom or (config.NO_DIRECTION and sentence_token.lemma_ in [x.lemma_ for x in idiom_subtree]):
						sentence_top_token = sentence_token
						# Keep track of indices of matching tokens for later span extraction
						matched_indices = [sentence_top_token.i] 
						# Match parse trees, account for many special cases
						for idiom_subtree_token in idiom_subtree:
							# Skip top token and articles
							if idiom_subtree_token != idiom_top_token and idiom_subtree_token.lower_ not in ['a', 'the', 'an']:
								matched_subtree_token = False
								for sentence_subtree_token in sentence_token.subtree:
									# Match condition components
									# Spacy gives same lemma for all pronouns, so match on lower-cased form 
									matching_lemma = (idiom_subtree_token.lemma_ == sentence_subtree_token.lemma_ and idiom_subtree_token.lemma_ != u'-PRON-') or (idiom_subtree_token.lemma_ == u'-PRON-' and idiom_subtree_token.lower_ == sentence_subtree_token.lower_)
									# Optionally, ignore dependency labels
									matching_dep = idiom_subtree_token.dep_ == sentence_subtree_token.dep_ or config.NO_LABELS
									matching_head_lemma = (idiom_subtree_token.head.lemma_ == sentence_subtree_token.head.lemma_ and idiom_subtree_token.head.lemma_ != u'-PRON-') or (idiom_subtree_token.head.lemma_ == u'-PRON-' and idiom_subtree_token.head.lower_ == sentence_subtree_token.head.lower_)
									# Optionally, allow for direction reversal
									if config.NO_DIRECTION:
										if idiom_subtree_token.head.lemma_ == u'-PRON-':
											matched_children = [x for x in sentence_subtree_token.children if x.lower_ == idiom_subtree_token.head.lower_]
										else:
											matched_children = [x for x in sentence_subtree_token.children if x.lemma_ == idiom_subtree_token.head.lemma_]
										matching_child_lemma = matched_children != []
										matching_head_lemma = matching_head_lemma or matching_child_lemma
									em_dash_lemma = has_em_dash and idiom_subtree_token.lemma_ == ambiguous_word
									em_dash_head_lemma = has_em_dash and idiom_subtree_token.head.lemma_ == ambiguous_word
									inverted_dep = idiom_subtree_token.dep_ == 'dobj' and sentence_subtree_token.dep_ == 'nsubjpass' or config.NO_LABELS
									# Default case: lemma, dep-rel and head lemma have to match.
									# In case of em-dash, match lemma or head lemma, and the other one to the ambiguous word
									if (matching_lemma and matching_dep and matching_head_lemma or 
											em_dash_lemma and matching_head_lemma or 
											matching_lemma and em_dash_head_lemma):
										matched_subtree_token = True
									# Passivization: match lemma, head lemma and inverted dep-rels
									elif matching_lemma and inverted_dep and matching_head_lemma:
										matched_subtree_token = True
									# Deal with someone and someone's
									elif idiom_subtree_token.lemma_ == 'someone':
										idiom_right_children = [right for right in idiom_subtree_token.rights]
										# Deal with someone's - match any other PRP$ or NN(P)(S) + POS for lemma
										if idiom_right_children and idiom_right_children[0].lemma_ == "'s":
											sentence_right_children = [right for right in sentence_subtree_token.rights]
											if (matching_dep and matching_head_lemma and (sentence_subtree_token.tag_ == 'PRP$' or
													sentence_subtree_token.tag_ in ['NN', 'NNS', 'NNP', 'NNPS'] and 
													sentence_right_children and sentence_right_children[0].lemma_ == "'s")):
												matched_subtree_token = True
										# Deal with someone - match any other PRP or NN(P)(S) for lemma
										else:
											if ((matching_dep or inverted_dep) and matching_head_lemma and 
													sentence_subtree_token.tag_ in ['PRP', 'NN', 'NNS', 'NNP', 'NNPS']):
												matched_subtree_token = True
									# Deal with one's - match any PRP$ for lemma
									elif idiom_subtree_token.lemma_ == 'one':
										idiom_right_children = [right for right in idiom_subtree_token.rights]
										if idiom_right_children and idiom_right_children[0].lemma_ == "'s":
											if matching_dep and matching_head_lemma and sentence_subtree_token.tag_ == 'PRP$':
												matched_subtree_token = True
									# Deal with something and something's
									elif idiom_subtree_token.lemma_ == 'something':
										idiom_right_children = [right for right in idiom_subtree_token.rights]
										# Deal with something's - match any other PRP$ or NN(P)(S) + POS for lemma
										if idiom_right_children and idiom_right_children[0].lemma_ == "'s":
											sentence_right_children = [right for right in sentence_subtree_token.rights]
											if (matching_dep and matching_head_lemma and (sentence_subtree_token.tag_ == 'PRP$' or 
													sentence_subtree_token.tag_ in ['NN', 'NNS', 'NNP', 'NNPS'] and 
													sentence_right_children and sentence_right_children[0].lemma_ == "'s")):
												matched_subtree_token = True
										# Deal with something - match any other PRP or NN(P)(S) or this/that/these/those for lemma
										else:
											if ((matching_dep or inverted_dep) and matching_head_lemma and 
													(sentence_subtree_token.tag_ in ['PRP', 'NN', 'NNS', 'NNP', 'NNPS'] or 
													sentence_subtree_token.lemma_ in ['this', 'that', 'these', 'those'])):
												matched_subtree_token = True
									# Deal with 's of someone's, one's and something's by ignoring it
									elif idiom_subtree_token.lemma_ == "'s" and idiom_subtree_token.head.lemma_ in ['someone', 'one', 'something']:
										matched_subtree_token = True
										break

									if matched_subtree_token: # Match, go to next idiom subtree token
										# Add child in case of no-directionality child match
										if config.NO_DIRECTION and matching_child_lemma:
											matched_indices.append(matched_children[0].i)
										else:
											matched_indices.append(sentence_subtree_token.i)
										break
								if not matched_subtree_token: # No match, go to next sentence token
									break

						# If everything matches, extract snippet
						if matched_subtree_token:
							# Text of idiom subtree is dictionary form
							dictionary_form = ''.join([idiom_subtree_token.text_with_ws for idiom_subtree_token in idiom_subtree]).strip()
							# Deal with em-dash wildcard idiom, substitute em-dash back in for ambiguous word
							if has_em_dash:
								dictionary_form = re.sub(ambiguous_word, u'\u2014', dictionary_form)
							# Get idiom token span
							first_idiom_token_i = min(matched_indices) - parsed_sentence.start
							last_idiom_token_i = max(matched_indices) - parsed_sentence.start
							first_idiom_token = parsed_sentence[first_idiom_token_i]
							last_idiom_token = parsed_sentence[last_idiom_token_i]
							# Extract n-word context
							if config.CONTEXT_TYPE == 'w':
								span_start = max(0, first_idiom_token_i - config.CONTEXT_NUMBER)
								span_end = min(len(parsed_sentence), last_idiom_token_i + 1 + config.CONTEXT_NUMBER)
								snippet = parsed_sentence[span_start:span_end].text
								# Store character offset of snippet start
								char_offset_span = parsed_sentence[span_start].idx
							# Extract n-sentence context
							elif config.CONTEXT_TYPE == 's':
								if config.CONTEXT_NUMBER == 0:
									snippet = parsed_sentence.text
									# Store character offset of sentence (==snippet) start
									char_offset_span = parsed_sentence.start_char
								else:
									snippet = ""
									# Get snippet sentences
									first_sentence_idx = sentence_idx - config.CONTEXT_NUMBER
									last_sentence_idx = sentence_idx + config.CONTEXT_NUMBER
									# Re-iterate over sentences to extract the sentence contents
									for sentence_idx_2, parsed_sentence_2 in enumerate(parsed_corpus.sents):
										if sentence_idx_2 >= first_sentence_idx and sentence_idx_2 <= last_sentence_idx:
											# Store character offset of snippet start
											if sentence_idx_2 == first_sentence_idx:
												char_offset_span = parsed_sentence_2.start_char
											# Add space between sentences
											if snippet: 
												snippet += ' ' 
											snippet += parsed_sentence_2.text
							# Get idiom character offsets in snippet
							char_offset_start = first_idiom_token.idx - char_offset_span
							char_offset_end = last_idiom_token.idx + len(last_idiom_token.text) - char_offset_span
							# Get BNC metadata/set dummy values
							if config.CORPUS_TYPE[0:3] == 'bnc':
								bnc_document_id = sentences_with_metadata[sentence_idx]['document_id']
								bnc_sentence = sentences_with_metadata[sentence_idx]['sentence_number']
								bnc_char_start = first_idiom_token.idx
								bnc_char_end = last_idiom_token.idx + len(last_idiom_token.text)
							else:
								bnc_document_id = '-'
								bnc_sentence = '-'
								bnc_char_start = 0
								bnc_char_end = 0
						
							extracted_idiom = {'snippet': snippet, 'idiom': dictionary_form, 'start': char_offset_start, 
								'end': char_offset_end,	'bnc_document_id': bnc_document_id, 'bnc_sentence': bnc_sentence,
								'bnc_char_start': bnc_char_start, 'bnc_char_end': bnc_char_end}

							# Check whether the instance has already been added, with a larger span (this can happen with em-dash idioms). Don't do this for NLD matches.
							if previously_matched_indices:
								# Remove most recent entry if it has a larger span than the current entry 
								if min(previously_matched_indices) <= min(matched_indices) and max(previously_matched_indices) >= max(matched_indices) and (sentence_token.lemma_ == idiom_top_token.lemma_ or consider_this_em_dash_idiom):
									del extracted_idioms[-1]
								# Only add current entry if it doesn't have a larger span than the most recent entry
								if not (min(previously_matched_indices) >= min(matched_indices) and max(previously_matched_indices) <= max(matched_indices)) and (sentence_token.lemma_ == idiom_top_token.lemma_ or consider_this_em_dash_idiom):
									extracted_idioms.append(extracted_idiom)
									previously_matched_indices = matched_indices
							else:
								extracted_idioms.append(extracted_idiom)
								previously_matched_indices = matched_indices

	return extracted_idioms

if __name__ == '__main__':
	print 'Hello! Time is {0}'.format(config.TIME)

	# Create working directory if it doesn't exist
	if not os.path.isdir(config.WORK_DIR):
		os.mkdir(config.WORK_DIR)

	# Read in corpus as list of documents
	if config.CORPUS_TYPE == 'plain':
		documents = process_corpus.plain_text(config.CORPUS, config.NO_SPLIT)
		print 'First sentence of corpus: {0}\nLast sentence of corpus: {1}'.format(u8(documents[0][0]), u8(documents[-1][-1]))
	elif config.CORPUS_TYPE[0:3] == 'bnc':
		cache_path = os.path.join(config.WORK_DIR, '{0}_parsed_xml.json'.format(config.CORPUS_TYPE))
		documents = process_corpus.bnc(config.CORPUS, config.CORPUS_TYPE, cache_path)
		print 'First sentence of corpus: {0}\nLast sentence of corpus: {1}'.format(u8(documents[0][0]['sentence']), u8(documents[-1][-1]['sentence']))

	# Get idioms from dictionary
	idioms = get_idiom_list(case_sensitive = config.CASE_SENSITIVE)
	print "Found {4} idioms ranging from '{0}', '{1}' to '{2}', '{3}'".format(u8(idioms[0]), u8(idioms[1]), u8(idioms[-2]), u8(idioms[-1]), len(idioms))

	# Extract idioms
	extraction_start = time.time()
	if config.METHOD == 'exact':
		extracted_idioms = string_match(idioms, documents, fuzzy = False, inflect = False, case_sensitive = config.CASE_SENSITIVE)
	elif config.METHOD == 'fuzzy':
		extracted_idioms = string_match(idioms, documents, fuzzy = True, inflect = False, case_sensitive = config.CASE_SENSITIVE)
	elif config.METHOD == 'inflect':
		extracted_idioms = string_match(idioms, documents, fuzzy = False, inflect = True, case_sensitive = config.CASE_SENSITIVE)
	elif config.METHOD == 'parse':
		extracted_idioms = parse_extract(idioms, documents)

	# Print information about extracted idioms
	print 'Extracted {0} idioms in {1:.2f} seconds'.format(len(extracted_idioms), time.time() - extraction_start)
	idiom_set = set([extracted_idiom['idiom'] for extracted_idiom in extracted_idioms])
	if len(idiom_set) >= 5:
		idiom_sample = random.sample(idiom_set, 5)
		print 'Extracted these idioms, among others: {0}, {1}, {2}, {3}, {4}'.format(u8(idiom_sample[0]), u8(idiom_sample[1]), u8(idiom_sample[2]), u8(idiom_sample[3]), u8(idiom_sample[4]))

	# Output extracted idioms to file 
	utils.write_csv(extracted_idioms, config.OUTFILE)
