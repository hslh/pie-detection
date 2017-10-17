#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Combine the output of two runs of the PIE extraction system, removing duplicates.
'''

import json, argparse, csv, copy

from utils import u8

# Read in arguments
parser = argparse.ArgumentParser(description = 'Parameters for PIE extraction evaluation')
parser.add_argument('extracted_1', metavar = 'extracted_idioms_1.csv', type = str, help = "Specify the location of the first file containing the extracted PIEs.")
parser.add_argument('extracted_2', metavar = 'extracted_idioms_2.csv', type = str, help = "Specify the location of the second file containing the extracted PIEs.")
parser.add_argument('combined', metavar = 'combined_idioms.csv', type = str, help = "Specify the output location of the combined set of extracted PIEs.")
args = parser.parse_args()

# Read input data
extracted_idioms_1 = []
with open(args.extracted_1, 'r') as csvfile:
	csvreader = csv.reader(csvfile, delimiter = '\t', quoting=csv.QUOTE_MINIMAL, quotechar = '"')
	for csvrow in csvreader:
		extracted_idioms_1.append({'document_id': csvrow[4], 'sentence_number': csvrow[5], 'idiom': csvrow[0], 'context': unicode(csvrow[3], 'utf-8'), 'start': csvrow[1], 'end': csvrow[2], 'bnc_start': csvrow[6], 'bnc_end': csvrow[7]})
extracted_idioms_2 = []
with open(args.extracted_2, 'r') as csvfile:
	csvreader = csv.reader(csvfile, delimiter = '\t', quoting=csv.QUOTE_MINIMAL, quotechar = '"')
	for csvrow in csvreader:
		extracted_idioms_2.append({'document_id': csvrow[4], 'sentence_number': csvrow[5], 'idiom': csvrow[0], 'context': unicode(csvrow[3], 'utf-8'), 'start': csvrow[1], 'end': csvrow[2], 'bnc_start': csvrow[6], 'bnc_end': csvrow[7]})
	
# Combine two sets of extractions
combined_idioms = copy.deepcopy(extracted_idioms_1)
for extracted_idiom_2 in extracted_idioms_2:
	matched = False
	for extracted_idiom_1 in extracted_idioms_1:
		if extracted_idiom_2['idiom'].lower() == extracted_idiom_1['idiom'].lower() and extracted_idiom_2['document_id'] == extracted_idiom_1['document_id'] and extracted_idiom_2['sentence_number'] == extracted_idiom_1['sentence_number']:
			matched = True
			break
	if not matched:
		combined_idioms.append(extracted_idiom_2)

# Output to file	
with open(args.combined, 'w') as of:
	writer = csv.writer(of, delimiter = '\t', quoting=csv.QUOTE_MINIMAL, quotechar = '"')
	for extracted_idiom in combined_idioms:
		output_row = [u8(extracted_idiom['idiom']), extracted_idiom['start'], extracted_idiom['end'], 
			u8(extracted_idiom['context']), u8(extracted_idiom['document_id']), u8(extracted_idiom['sentence_number']), 
			extracted_idiom['bnc_start'], extracted_idiom['bnc_end']]
		writer.writerow(output_row)
