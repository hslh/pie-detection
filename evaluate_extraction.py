#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Evaluate PIE extraction performance against an exhaustively PIE annotated corpus, output recall, precision and F1-score.
'''

import json, argparse, csv, random
from collections import Counter

# Read in arguments
parser = argparse.ArgumentParser(description = 'Parameters for PIE detection evaluation')
parser.add_argument('extracted', metavar = 'extracted_idioms.csv', type = str, help = "Specify the file containing the extracted PIEs.")
parser.add_argument('annotated', metavar = 'annotated_idioms.json', type = str, help = "Specify the file containing the annotated PIEs")
args = parser.parse_args()

# Read input data
extracted_idioms = []
with open(args.extracted, 'r') as csvfile:
	csvreader = csv.reader(csvfile, delimiter = '\t', quoting=csv.QUOTE_MINIMAL, quotechar = '"')
	for csvrow in csvreader:
		extracted_idioms.append({'document_id': csvrow[4], 'sentence_number': csvrow[5], 'idiom': csvrow[0], 'context': unicode(csvrow[3], 'utf-8'), 'start': csvrow[1], 'end': csvrow[2]})
		
annotated_idioms = json.load(open(args.annotated, 'r'))

# Check if datasets cover same documents
assert set([idiom['document_id'] for idiom in extracted_idioms]) <= set([idiom['document_id'] for idiom in annotated_idioms])

# Select only the PIEs from the set of annotated PIE candidates
annotated_idioms = [annotated_idiom for annotated_idiom in annotated_idioms if annotated_idiom['PIE_label'] == 'y']

# Keep track of false negatives
for annotated_idiom in annotated_idioms:
	annotated_idiom['evaluation'] = 'fn'

# Count true/false positives/negatives
# We do not have true negatives
tp = 0.
fp = 0.
fn = 0.
for extracted_idiom in extracted_idioms:
	for annotated_idiom in annotated_idioms:
		# Lower case PIEs for comparison, as they are annotated as lower-case, but not necessarily extracted so 
		if extracted_idiom['document_id'] == annotated_idiom['document_id'] and extracted_idiom['sentence_number'] == annotated_idiom['sentence_number'] and extracted_idiom['idiom'].lower() == annotated_idiom['idiom'].lower():
			tp += 1
			extracted_idiom['evaluation'] = 'tp'
			annotated_idiom['evaluation'] = 'tp'
			break
	else: # No break 
		fp += 1
		extracted_idiom['evaluation'] = 'fp'
		
fn = len(annotated_idioms) - tp # False negatives = all missed PIEs = # annotated PIEs - # correctly found PIEs

# Get precision, recall, F1-score
precision = tp / (tp + fp)
recall = tp / (tp + fn)
f1 = 2 * (precision * recall) / (precision + recall)

# Print results
print '### RESULTS ###'
print 'Total number of annotated PIEs: {0}'.format(len(annotated_idioms))
print 'Total number of extracted PIEs: {0}\n'.format(len(extracted_idioms))
print 'True Positives: {0}\nFalse Positives: {1}\nFalse Negatives: {2}\n'.format(tp, fp, fn)
print 'Precision: {0}%'.format(precision*100)
print 'Recall: {0}%'.format(recall*100)
print 'F1-score: {0}%'.format(f1*100)

# Print examples of classifications
def show_examples(idioms, evaluation):
	# Define colours
	stop = '\x1b[0m'
	red = '\x1b[1;31;1m'
	# Count number of examples shown
	count = 0
	for idiom in idioms:
		if idiom['evaluation'] == evaluation:
			# Highlight idiom in context 
			try:
				context = idiom['context']
				start = int(idiom['start'])
				end = int(idiom['end'])
			except KeyError:
				context = idiom['sentence']
				start = idiom['offsets'][0][0]
				end = idiom['offsets'][-1][-1]
			highlighted_context = context[:start]
			highlighted_context += red
			highlighted_context += context[start:end]
			highlighted_context += stop
			highlighted_context += context[end:]
			print highlighted_context,
			print '({2} - doc. {0} - sent. {1})'.format(idiom['document_id'], idiom['sentence_number'], idiom['idiom'])
			count += 1
			if count % 10 == 0:
				user_input = unicode(raw_input("Show 10 more examples? (y/n): "), 'utf-8')
				if user_input.lower() != 'y':
					break
	else: # No break
		print 'No more examples!'

# Prompt and show examples for different classes
# Shuffle idiom lists to avoid seeing same examples again and again
random.shuffle(extracted_idioms) 
random.shuffle(annotated_idioms) 
user_input = unicode(raw_input("Show examples of classifications? (y/n): "), 'utf-8')
if user_input.lower() == 'y':
	user_input = unicode(raw_input("Show examples of true positives? (y/n): "), 'utf-8')
	if user_input.lower() == 'y':
		show_examples(extracted_idioms, 'tp')
	user_input = unicode(raw_input("Show examples of false positives? (y/n): "), 'utf-8')
	if user_input.lower() == 'y':
		show_examples(extracted_idioms, 'fp')
	user_input = unicode(raw_input("Show examples of false negatives? (y/n): "), 'utf-8')
	if user_input.lower() == 'y':
		show_examples(annotated_idioms, 'fn')			

# Split performance for most frequent PIE types in corpus
def performance_per_type(annotated_idioms, extracted_idioms, n):
	most_frequent_types = Counter([x['idiom'] for x in annotated_idioms]).most_common()
	print 'PIE Type' + 17*' ' + 'Count\tPrecision\tRecall\tF1-score'
	for pie_type in most_frequent_types[:n]:
		pie = pie_type[0]
		count = pie_type[1]
		tp = float(len([x['evaluation'] for x in extracted_idioms if x['idiom'] == pie and x['evaluation'] == 'tp']))
		fp = float(len([x['evaluation'] for x in extracted_idioms if x['idiom'] == pie and x['evaluation'] == 'fp']))
		fn = float(len([x['evaluation'] for x in annotated_idioms if x['idiom'] == pie and x['evaluation'] == 'fn']))
		try:
			precision = tp / (tp + fp)
			recall = tp / (tp + fn)
			f1 = 2 * (precision * recall) / (precision + recall)
		except ZeroDivisionError:
			precision = 0.
			recall = 0.
			f1 = 0.
		pie += (25 - len(pie)) * ' '
		print '{0}{1}\t{2:.2f}\t\t{3:.2f}\t{4:.2f}'.format(pie, count, precision * 100, recall * 100, f1 * 100)
		
user_input = unicode(raw_input("Show performance for 25 most frequent PIE types? (y/n): "), 'utf-8')
if user_input.lower() == 'y':
	performance_per_type(annotated_idioms, extracted_idioms, 25)
