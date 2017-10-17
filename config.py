#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Set parameters, parse and validate command-line arguments'''

import argparse, os, datetime, re

# Non-argument parameters
WORK_DIR = './working'
EXT_DIR = './ext'
MORPH_DIR = os.path.join(EXT_DIR, 'morph')
TIME = '{:%Y-%m-%d-%H-%M-%S}'.format(datetime.datetime.now())
UE_URL = 'https://www.usingenglish.com'
UE_IDOMS_URL = UE_URL + '/reference/idioms'
OX_URL = 'http://www.oxfordreference.com'
OX_LANDING_URL = OX_URL + '/view/10.1093/acref/9780199543793.001.0001/acref-9780199543793?pageSize=100' # Requires access through e.g. a library

# Read in arguments
parser = argparse.ArgumentParser(description = 'Parameters for PIE detection')
parser.add_argument('-d', '--dict', metavar = 'wiktionary|ue|oxford|intersection|2of3|union', type = str, default = 'wiktionary', help = "Specify which dictionary to use, default is 'wiktionary'. Other options are 'ue' for UsingEnglish.com, 'oxford' for Oxford Dictionary of English Idioms, 'intersection' for idioms occurring in all three dictionaries, '2of3' for idioms occurring in at least two of the three dictionaries, and 'union' for all idioms occurring in at least one of the three dictionaries. To get the intersection of a pair of dictionaries, enter two dictionary names, separated by a comma, e.g. 'wiktionary,oxford'.")
parser.add_argument('corpus', metavar = 'CORPUS', type = str, help = "Specify the location of the corpus to extract PIEs from.")
parser.add_argument('-t', '--corpus-type', metavar = 'plain|bnc|bnc-dev|bnc-test', type = str, default = 'plain', help = "Specify the type of corpus used. Plain text or BNC (all and dev/test sets).")
parser.add_argument('-m', '--method', metavar = 'exact|fuzzy|inflect|parse', type = str, default = 'exact', help = "Specify the extraction method to use. 'exact' for exact string matching, 'fuzzy' for fuzzy/ string matching, 'inflect' for inflectional string matching, 'parse' for parse-based extraction.")
parser.add_argument('-p', '--parser', metavar = 'spacy|stanford', type = str, default = 'spacy', help = "Specify whether to use the Spacy or Stanford parser for parse-based extraction")
parser.add_argument('-ex', '--example-sentences', metavar = 'CORPUS', type = str, help = "With the 'parse' method, specify this option to retrieve example sentences for in-context parsing. Specify a path to a corpus or to the file containing the cached output of this method.")
parser.add_argument('-iw', '--intervening-words', metavar = 'N', type = int, default = 0, help = "Number of intervening words allowed between words of an idiom in the string match methods. Default is 0.")
parser.add_argument('-c', '--context', metavar = '{0-9}+{ws}', type = str, default = '0s', help = "Amount of context to extract around the idiom. Can be a number of words or sentences. '0w' will yield only the idiom, '1w' one word of context on both sides of the idiom, etc. Word-contexts never exceed sentence boundaries. '0s' will yield only the sentence containing the idiom.")
parser.add_argument('-o', '--output', metavar = 'OUTFILE', type = str, help = "Specify where to output the extracted idioms. Default is WORK_DIR/extracted_idioms_from_CORPUS_NAME_TIMESTAMP.")
parser.add_argument('-nc', '--no-cache', action = 'store_true', help = "Do not use a cached idiom list.")
parser.add_argument('-ns', '--no-split', action = 'store_true', help = "In case of a one-sentence-per-line corpus, do not apply automatic sentence splitting. Does not affect parser-based extraction.")
parser.add_argument('-cs', '--case-sensitive', action = 'store_true', help = "Make string-matching methods case sensitive.")
parser.add_argument('-nl', '--no-labels', action = 'store_true', help = "Ignore dependency relation labels during parse-based extraction")
parser.add_argument('-nld', '--no-labels-or-directionality', action = 'store_true', help = "Ignore dependency relation labels AND dependency relation direction during parse-based extraction.")
args = parser.parse_args()

# Store arguments as parameters and do validation
DICT = args.dict.split(',')
if len(DICT) == 1 and DICT[0] not in ['wiktionary', 'ue', 'oxford', 'intersection', '2of3', 'union']:
	raise ValueError("No valid dictionary option specified.")
elif len(DICT) == 2 and (DICT[0] not in ['wiktionary', 'ue', 'oxford'] or DICT[1] not in ['wiktionary', 'ue', 'oxford']):
	raise ValueError("No valid dictionary option specified.")
elif len(DICT) < 1 or len(DICT) > 2:
	raise ValueError("No valid dictionary option specified.")

CORPUS = os.path.abspath(args.corpus)
if not os.path.exists(CORPUS):
	raise ValueError("Corpus not found.")

if args.corpus_type in ['plain', 'bnc', 'bnc-dev', 'bnc-test']:
	CORPUS_TYPE = args.corpus_type
else:
	raise ValueError("No valid corpus type specified.")

if args.method in ['exact', 'fuzzy', 'inflect', 'parse']:
	METHOD = args.method
else:
	raise ValueError("No valid extraction method specified.")

if args.parser.lower() in ['spacy', 'stanford']:
	PARSER = args.parser.lower()
else:
	raise ValueError("No valid parser specified.")

INT_WORDS = args.intervening_words

SENTENCES = args.example_sentences
if SENTENCES:
	SENTENCES = os.path.abspath(args.example_sentences)

if re.match('[0-9]+[ws]', args.context):
	CONTEXT_NUMBER = int(args.context[:-1])
	CONTEXT_TYPE = args.context[-1]
else:
	raise ValueError("No valid context window argument provided. Should be of the format [0-9]+[ws].")	

if not args.output: # Set default
	OUTFILE = os.path.abspath(os.path.join(WORK_DIR, 'extracted_idioms_from_{0}_{1}.csv'.format(CORPUS.split('/')[-1],TIME)))
else: 
	OUTFILE = os.path.abspath(args.output)

NO_CACHE = args.no_cache
NO_SPLIT = args.no_split
CASE_SENSITIVE = args.case_sensitive
NO_LABELS = args.no_labels or args.no_labels_or_directionality
NO_DIRECTION = args.no_labels_or_directionality
