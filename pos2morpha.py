#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Based on a similar script by Kilian Evang

'''
Converts tokenized and POS-tagged texts in C&C format (pipe-separated PTB tags)
to morpha's input format (underscore-separated CLAWS tags).
'''

import re, sys

def ptb2claws(token, tag):
    if tag == 'NNP': 
		return 'NP'
    if tag == 'NNPS': 
		return 'NP2'
    if tag == 'NNS': 
		return 'NN2'
    if token in ('ca', 'sha', 'wo', '\'d') and tag == 'MD': 
		return 'VM'
    if token == 'n\'t' and tag == 'RB': 
		return 'XX'
    if token == '\'d' and tag == 'VBD': 
		return 'VH'
    return tag

def convert_token(token):
    pipeindex = token.rfind('|')
    prefix = token[:pipeindex]
    suffix = token[pipeindex + 1:]
    if len(prefix) > 1 and prefix.endswith('-'):
        prefix = prefix[:-1]
    return prefix + '_' + ptb2claws(prefix, suffix)

