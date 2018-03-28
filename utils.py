#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Utility functions to work with morpha, PoS-tagging, parsing, and other things.'''

import pos2morpha

import subprocess, shlex, time, json, re, itertools, csv
import spacy
import en_core_web_sm as spacy_model 
from stanfordcorenlp import StanfordCoreNLP
import nltk.data

###### STANFORD TO SPACY ######
class StanfordDoc:
	'''Spacy-Doc-like container for Stanford output'''

	def __init__(self):
		self.sents = []

	def __iter__(self):
		return iter(self.tokens)

	def __getitem__(self, i):
		if isinstance(i, slice):
			return StanfordSpan(self.tokens[i.start:i.stop])
		else:
			return self.tokens[i]

	# Generate list of tokens from sentences
	def set_tokens(self):
		self.tokens = [token for sent in self.sents for token in sent]

class StanfordSpan:
	'''Spacy-Span-like container for Stanford output'''

	def __init__(self, tokens):
		self.tokens = tokens
		self.start = self.tokens[0].i # Starting token index in document
		self.start_char = self.tokens[0].idx # Starting character index in document
		self.text_with_ws = ''.join([token.text_with_ws for token in self.tokens])
		self.text = ''.join([token.text_with_ws for token in self.tokens[:-1]]) + self.tokens[-1].text

	def __iter__(self):
		return iter(self.tokens)

	def __getitem__(self, i):
		return self.tokens[i]

class StanfordToken:
	'''Spacy-Token-like container for Stanford output'''

	def __init__(self, i, idx, lemma, tag, text, ws, word, doc):
		self.i = i # Token index in document
		self.idx = idx # Starting character index in document
		self.lemma_ = lemma
		self.tag_ = tag # PoS-tag inventory might differ slightly, but should not cause problems
		self.text = text
		self.text_with_ws = text + ws
		self.lower_ = word.lower()
		self.children = []
		self.doc = doc

	def __str__(self):
		return self.text

	# Recursively gets all the syntactic descendants of a token, including self
	def get_descendants(self):
		descendants = [self]
		for child in self.children:
			descendants += child.get_descendants()
		return descendants

	# Sets the subtree attribute, which is an ordered generator for all descendants of a token
	def get_subtree(self):
		return sorted(self.get_descendants(), key=lambda x: x.i)

	# Sets the rights attribute, which is an ordered generator for all children to the right of a token
	def get_rights(self):
		return [child for child in self.children if child.i > self.i]

	def __repr__(self):
		return self.text

def stanford_to_spacy(parse):
	'''Turn Stanford CoreNLP output into a Spacy-like object'''

	# Convert into Spacy-like objects
	doc = StanfordDoc()
	doc_i = 0
	for sentence in parse['sentences']:
		span = []
		# Get token information
		tokens = sentence['tokens']
		dependencies = sentence['basicDependencies']
		# Make tokens into StanfordTokens
		for token in tokens:
			new_token = StanfordToken(doc_i, token['characterOffsetBegin'], token['lemma'], token['pos'], token['originalText'], token['after'], token['word'], doc)
			doc_i += 1
			span.append(new_token)
		# Add dependency relation and head index to tokens
		for dependency in dependencies:
			span[dependency['dependent'] - 1].head_idx = dependency['governor'] - 1
			span[dependency['dependent'] - 1].dep_ = dependency['dep']
		# Add pointer to head of each token
		for new_token in span:
			# ROOT has itself as head
			try:
				if new_token.head_idx == -1:
					new_token.head = new_token
				else:
					new_token.head = span[new_token.head_idx]
					new_token.head.children.append(new_token)
			# Occasionally, a misformed parse yields a token without a head, default to ROOT, and show problematic sentence
			except AttributeError:
				new_token.head_idx = -1
				new_token.dep_ = u'ROOT'
				new_token.head = new_token
				print 'Headless word \'{0}\' in sentence "{1}"'.format(new_token.text.encode('utf-8'), ''.join([x.text_with_ws.encode('utf-8') for x in span]))
		# Add subtree to each token
		for new_token in span:
			new_token.subtree = new_token.get_subtree()
			new_token.rights = new_token.get_rights()
		doc.sents.append(StanfordSpan(span))
	# Generate token list
	doc.set_tokens()
	
	return doc

###### PARSING ######
def load_parser(parser_type):
	'''Loads Spacy or Stanford CoreNLP'''

	time_0 = time.time()
	print 'Loading parser...'
	if parser_type == 'spacy':
		parser = spacy_model.load()
	elif parser_type == 'stanford':
		parser = StanfordCoreNLP('ext/stanford', memory='6g')
		parse((parser_type, parser), 'The cat sat on the mat.') # Annotate dummy sentence to force loading of annotation modules
	print 'Done! Loading parser took {0:.2f} seconds'.format(time.time() - time_0)

	return (parser_type, parser)

def parse(parser, text):
	'''Parses a (unicode) string and returns the parse.'''

	if parser[0] == 'spacy':
		# Convert to unicode if necessary
		try:
			text = unicode(text, 'utf-8')
		except TypeError:
			pass
		# Normalize quotes, ‘ ’ ❛ ❜ to ', and “ ” ❝ ❞ to ", Spacy doesn't process them well
		text = re.sub(u'‘|’|❛|❜', u"'", text)
		text = re.sub(u'“|”|❝|❞', u'"', text)
		# Insert a space between punctuation and a dash, Spacy doesn't process that well either
		text = re.sub(ur'([^\w\s])([-—])', r'\1 \2', text)
		return parser[1](text)

	if parser[0] == 'stanford':
		# Convert from unicode if necessary
		try:
			text = text.encode('utf-8')
		except UnicodeDecodeError:
			pass
		properties={'annotators': 'tokenize,ssplit,pos,lemma,depparse','pipelineLanguage':'en','outputFormat':'json'}
		parsed_text = parser[1].annotate(text, properties=properties)
		parsed_text = json.loads(parsed_text)
		return stanford_to_spacy(parsed_text)

###### POS-TAGGING ######
def load_pos_tagger():
	'''Loads Spacy PoS-tagger which takes pre-tokenized text.'''
	
	time_0 = time.time()
	print 'Loading PoS-tagger...'
	pos_tagger = spacy_model.load(disable = ['ner', 'parser'])
	print 'Done! Loading PoS-tagger took {0:.2f} seconds'.format(time.time() - time_0)

	return pos_tagger

def pos_tag(pos_tagger, text):
	'''Takes pos_tagger and tokenized utf-8 idiom/sentence, returns list of word|POS strings.'''
	
	# Normalize quotes, ‘ ’ ❛ ❜ to ', and “ ” ❝ ❞ to ", Spacy doesn't process them well
	text = re.sub(u'‘|’|❛|❜', u"'", text)
	text = re.sub(u'“|”|❝|❞', u'"', text)
	# Make Doc
	doc = spacy.tokens.Doc(pos_tagger.vocab, text.split())
	# Set sentence boundary
	for token in doc:
		if token.i == 0:
			token.is_sent_start = True
		else:
			token.is_sent_start = False
	# Do actual tagging
	doc = pos_tagger.tagger(doc)
	# Convert into list of words and tags
	words_and_tags = []
	for token in doc:
		words_and_tags.append(token.text + u'|' + token.tag_)
		
	return words_and_tags

###### MORPHA ######	
def morpha(morph_dir, tokens, keep_case = True, keep_pos = False):
	'''Interface to morpha and its options, takes list of tokens as input, returns list of uninflected tokens.'''

	# Set flags
	if keep_case:
		case_flag = 'c'
	else:
		case_flag = ''
	if keep_pos:
		pos_flag = 't'
	else:
		pos_flag = ''
	flags = '-{0}{1}f'.format(case_flag, pos_flag)

	# Call morpha via subprocess
	call = shlex.split('{0}/morpha {1} {0}/verbstem.list'.format(morph_dir, flags))
	process = subprocess.Popen(call, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	output = process.communicate(input=' '.join(tokens))
	base_tokens = output[0].split(' ')

	return base_tokens

def morphg(morph_dir, tokens, keep_case = True, keep_pos = False):
	'''Interface to morphg and its options, takes list of token+inflection_POS strings as input, returns tuple of inflected tokens.'''

	# Set flags
	if keep_case:
		case_flag = 'c'
	else:
		case_flag = ''
	if keep_pos:
		pos_flag = 't'
	else:
		pos_flag = ''
	flags = '-{0}{1}f'.format(case_flag, pos_flag)

	# Call morphg
	call = shlex.split('{0}/morphg {1} {0}/verbstem.list'.format(morph_dir, flags))
	process = subprocess.Popen(call, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	output = process.communicate(input=' '.join(tokens))
	inflected_tokens = output[0].split(' ')

	# Filter out failed inflections, which will still contain '+'
	cleaned_inflected_tokens = [i_t for i_t in inflected_tokens if not '+' in i_t]

	return tuple(cleaned_inflected_tokens)

###### TOKENIZATION ######
def load_tokenizer():
	'''Loads Spacy tokenizer'''

	time_0 = time.time()
	print 'Loading tokenizer...'
	tokenizer = spacy_model.load(disable = ['tagger', 'ner', 'parser'])
	print 'Done! Loading tokenizer took {0:.2f} seconds'.format(time.time() - time_0)

	return tokenizer

def tokenize(tokenizer, sentence):
	'''Parses a (unicode) sentence, returns list of Spacy Tokens'''
	try:
		return tokenizer(unicode(sentence, 'utf-8'))
	except TypeError:
		return tokenizer(sentence)

###### EXAMPLE SENTENCES ######
def get_example_sentences(idioms, sentences_file, cache_file):
	'''
	Takes a list of idioms, searches a large corpus for example sentences,
	extracts shortest example sentence, returns dict of format {idiom: sentence}.
	Saves extracted sentences and idioms to file, for fast re-use in subsequent runs. 
	'''

	time_0 = time.time()
	idioms_with_sentences = {}

	# If file is cached example sentences, load those, else extract sentences from corpus
	if re.search('.json$', sentences_file):
		idioms_with_sentences = json.load(open(sentences_file, 'r'))
		if set(idioms) <= set(idioms_with_sentences.keys()):
			print 'Using cached example sentences from {0}'.format(sentences_file)
			# Select only the idioms part of the idiom dictionary 
			if set(idioms) < set(idioms_with_sentences.keys()):
				idioms_with_sentences = {key: idioms_with_sentences[key] for key in idioms_with_sentences if key in idioms}
			return idioms_with_sentences
		else:
			raise Exception('{0} does not contain entries for all the idioms specified in the dictionary argument, quitting.'.format(sentences_file))
	else:
		print '{0} is not a cached json-file, extracting sentences containing idioms...'.format(sentences_file)

	# Add fallback option: no example sentence
	for idiom in idioms:
		idioms_with_sentences[idiom] = '' 
	# Compile idiom regexes for efficiency and ignore meta-linguistic uses in quotes
	idiom_regexes = [re.compile('[^"\'] ' + idiom + ' [^"\']') for idiom in idioms]
	# Find shortest (in tokens) sentence containing idiom in corpus
	splitter = nltk.data.load('tokenizers/punkt/english.pickle')
	# Extract first 1000 lines containing the idiom with grep, then split and find sentences
	for idx, idiom in enumerate(idioms):
		if idx%100 == 0 and idx > 0:
			print '\tGetting example sentences for {0} of {1} idioms took {2} seconds'.format(idx, len(idioms), time.time()-time_0)
		call = shlex.split('grep -m 1000 "{0}" {1}'.format(u8(idiom), sentences_file))
		process = subprocess.Popen(call, stdin=subprocess.PIPE, stdout = subprocess.PIPE, stderr=subprocess.PIPE)
		output = process.communicate()
		output = output[0].strip()
		sentences = splitter.tokenize(unicode(output, 'utf-8'))
		for sentence in sentences:
			if idiom_regexes[idx].search(sentence):
				# Should have at least 3 extra words in the 'sentence'
				if len(sentence.split(' ')) > len(idiom.split(' ')) + 3:
					if idioms_with_sentences[idiom]:
						# Replace old sentence if new sentence one is shorter
						if len(sentence.split(' ')) < len(idioms_with_sentences[idiom].split(' ')): 
							idioms_with_sentences[idiom] = sentence
					else:
						idioms_with_sentences[idiom] = sentence

	# Caching extracted example sentences
	ofn = cache_file
	with open(ofn, 'w') as of:
		json.dump(idioms_with_sentences, of)
		print 'Caching idioms and example sentences in {0}'.format(ofn)

	print 'Done! took {0:.2f} seconds'.format(time.time() - time_0)

	return idioms_with_sentences

def parse_example_sentences(idioms_with_sentences, ambiguous_word, parser):
	'''Parses an example sentence containing an idiom, returns the part of the parse tree spanning the idiom.'''

	parsed_idioms = []
	
	# Cycle through idioms, parse sentence if available, extract idiom-spanning subtree
	for idiom in idioms_with_sentences:
		sentence = idioms_with_sentences[idiom]
		if sentence:
			parsed_sentence = parse(parser, sentence)
			# Find indices of idiom in sentence
			start = re.search(idiom, sentence).start() 
			end = re.search(idiom, sentence).end()
			# Extract idiom subtree from parsed example sentence based on character offsets
			has_em_dash = u'\u2014' in idiom
			idiom_tokens = []
			subtree_start = None
			for token in parsed_sentence:
				if token.idx >= end:
					subtree_end = token.i
					break
				if token.idx >= start:
					if not subtree_start:
						subtree_start = token.i
					idiom_tokens.append(token)
			# Extract top token and lemma
			extracted = False
			for idiom_token in idiom_tokens:
				# If the head of current token is not part of the idiom, it is the top token of the idiom phrase
				if idiom_token.head.text not in idiom: 
					idiom_top_token = idiom_token
					idiom_top_lemma = idiom_token.lemma_
					# Detect parses where the idiom does not form a single subtree, parse those idioms w/o contenxt
					if extracted:
						del parsed_idioms[-1]
						parsed_idioms.append(parse_idiom(idiom, ambiguous_word, parser))
						break
					else:
						parsed_idioms.append((idiom_top_lemma, idiom_top_token, idiom_top_token.doc[subtree_start:subtree_end], has_em_dash))
						extracted = True

		# Parse the idiom if no sentence is available
		else:
			parsed_idioms.append(parse_idiom(idiom, ambiguous_word, parser))

	return parsed_idioms

###### IDIOM PROCESSING ######
def parse_idiom(idiom, ambiguous_word, parser):
	'''Parse idioms without context, extract top node, lemma and subtree.'''

	parsed_idiom = None # Format: (top_lemma, top_token, idiom subtree, has_em_dash)

	# Deal with em-dash wildcards, e.g. 'too - for words'. Replace wildcard with POS-ambiguous word (e.g. 'fine') and parse
	if u'\u2014' in idiom:
		has_em_dash = True
		parsed_idiom = parse(parser, re.sub(u'\u2014', ambiguous_word, idiom))
	else:
		has_em_dash = False
		parsed_idiom = parse(parser, idiom)

	# Extract top token and lemma
	for token in parsed_idiom:
		if token.dep_ == 'ROOT':
			idiom_top_lemma = token.lemma_	
			idiom_top_token = token
			idiom_subtree = []
	parsed_idiom = (idiom_top_lemma, idiom_top_token, idiom_subtree, has_em_dash)

	return parsed_idiom	

def inflect_idioms(idioms, morph_dir):
	'''
	Generate inflectional variants of idioms using the Spacy PoS-tagger,
	morpha and morphg. Takes a list of idioms, returns a list of inflected
	idioms and a mapping between inflectional variants and the base form.
	'''
	
	pos_tagger = load_pos_tagger()
	inflected_idioms = []
	base_form_map = {} # Maps inflectional variants to base form, format: {'inflectional variant': 'base form'}
	print 'Inflecting idioms...'
	time_0 = time.time()	

	for idiom in idioms:
		# Add original form to base form map
		base_form_map[idiom] = idiom
		# Tag tokens, convert to Morpha tags
		pos_tokens = pos_tag(pos_tagger, idiom)
		if pos_tokens:
			morpha_tokens = [pos2morpha.convert_token(pos_token).encode('utf-8') for pos_token in pos_tokens]
			# Run morpha
			base_tokens = morpha(morph_dir, morpha_tokens, keep_case = True, keep_pos = True)
			# Generate inflections for verbs and nouns
			base_tuples = []
			for base_token in base_tokens:
				# Look for NN, not N, because we don't want NP, proper names
				# Differentiate noun and verb inflections
				# Morphg doesn't handle 'be' well, define manually
				if base_token[0:4] == 'be_V':
					base_tuples.append(('be', 'being', 'been', 'am', 'are', 'is', 'was', 'were'))
				elif '_V' in base_token or '_NN' in base_token:
					if '_V' in base_token:
						morphg_tokens = (re.sub('_', '+s_', base_token), re.sub('_', '+ing_', base_token),
						re.sub('_', '+ed_', base_token), re.sub('_', '+en_', base_token))
					else:
						morphg_tokens = (re.sub('_', '+s_', base_token),)
					base_tuples.append((base_token.split('_')[0],) + morphg(morph_dir, morphg_tokens, keep_case = True, keep_pos = False))
				else:
					base_tuples.append((base_token.split('_')[0],))
			# Generate combinations of inflected tokens and store base form mapping
			for inflected_tokens in itertools.product(*base_tuples):
				inflected_idiom = unicode(' '.join(inflected_tokens), 'utf-8')
				inflected_idioms.append(inflected_idiom)
				base_form_map[inflected_idiom] = idiom

	# Join to original list, and filter out duplicates
	inflected_idioms = list(set(idioms + inflected_idioms))

	print 'Done! Inflecting idioms took {0:.2f} seconds'.format(time.time() - time_0)
	print 'With inflections, we have {0} idioms'.format(len(inflected_idioms))

	return inflected_idioms, base_form_map

def expand_indefinite_pronouns(idioms):
	'''
	When one's or someone's or someone occurs in an idiom, remove it,
	and add idioms with personal pronouns added in. Don't expand 'one',
	because it is too ambiguous.
	'''

	expanded_idioms = []
	base_form_map = {} # Maps expanded variants to base form, format: {'expanded idiom': 'base form'}
	possessive_pronouns = ['my', 'your', 'his', 'her', 'its', 'our', 'their']
	objective_pronouns = ['me', 'you', 'him', 'her', 'us', 'them', 'it']

	for idiom in idioms:
		# Add possessive pronouns only
		if re.search("\\bone's\\b", idiom):
			for possessive_pronoun in possessive_pronouns:
				expanded_idiom = re.sub("\\bone's\\b", possessive_pronoun, idiom)
				expanded_idioms.append(expanded_idiom)
				base_form_map[expanded_idiom] = idiom
		# Add possessive pronouns and a wildcard for other words
		elif re.search("\\bsomeone's\\b", idiom):
			for possessive_pronoun in possessive_pronouns + [unicode("—'s", 'utf-8')]:
				expanded_idiom = re.sub("\\bsomeone's\\b", possessive_pronoun, idiom)
				expanded_idioms.append(expanded_idiom)
				base_form_map[expanded_idiom] = idiom
		# Add objective pronouns and a wildcard for other words
		elif re.search("\\bsomeone\\b", idiom):
			for objective_pronoun in objective_pronouns + [unicode("—", 'utf-8')]:
				expanded_idiom = re.sub("\\bsomeone\\b", objective_pronoun, idiom)
				expanded_idioms.append(expanded_idiom)
				base_form_map[expanded_idiom] = idiom
		else: 
			expanded_idioms.append(idiom)
			base_form_map[idiom] = idiom

	return expanded_idioms, base_form_map

###### OUTPUT ######
def u8(u):
	'''Encode unicode string in utf-8.'''

	return u.encode('utf-8')
	
def write_csv(extracted_idioms, outfile):
	'''Writes extracted idioms to file in csv-format'''
	
	with open(outfile, 'w') as of:
		writer = csv.writer(of, delimiter = '\t', quoting=csv.QUOTE_MINIMAL, quotechar = '"')
		for extracted_idiom in extracted_idioms:
			output_row = [u8(extracted_idiom['idiom']), extracted_idiom['start'], extracted_idiom['end'], 
				u8(extracted_idiom['snippet']), u8(extracted_idiom['bnc_document_id']), u8(extracted_idiom['bnc_sentence']), 
				extracted_idiom['bnc_char_start'], extracted_idiom['bnc_char_end']]
			writer.writerow(output_row)
