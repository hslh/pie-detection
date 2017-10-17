# Automatic Detection of Potentially Idiomatic Expressions
This is the source code for a system to automatically detect potentially idiomatic expressiosn (PIEs, for short) in text. It has four different methods of doing so: exact string match, fuzzy string match, inflectional string match, and parse-based matching. It relies on a set of digitally available idiom dictionaries to get an inventory of expressions, and extracts all instances of those expressions (with context) from the input corpus.

## Requirements 
To run this code, you'll need the following Python setup:
* Python 2.7.6
* beautifulsoup4 4.5.1
* requests 2.17.3
* nltk 3.2.4
* spacy 1.8.2 + en_core_web_sm 1.2.0
* lxml 3.3.3

Different versions might work just as well, but cannot be guaranteed. 

You might also need:
* [morph](http://users.sussex.ac.uk/~johnca/morph.html), if you want to run inflectional string matching.
* [Stanford CoreNLP](https://stanfordnlp.github.io/CoreNLP/), if you want to run the parse-based method with the Stanford parser.
* the Python library [stanfordcorenlp](https://github.com/Lynten/stanford-corenlp) 3.7.0.2
* the [British National Corpus](http://www.natcorp.ox.ac.uk/), if you want to extract PIEs from that. 

## Getting Started
- Clone the repository
- Create subdirectories called `working` and `ext`
- If necessary: 
  - create a symlink `ext/morph` to the main directory of the morph tools
  - create a symlink `ext/stanford` to the main directory of your Stanford CorenNLP installation
  - create a symlink `ext/BNC` to the `Texts` directory of your copy of the BNC
- Try and run the system with `python detect_pies.py data/input_sample.txt -d wiktionary -t plain -m exact`. This should extract a list of idioms from Wiktionary and use the exact string match method to extract PIEs from the input sample file.
- Get an overview of all options by simply running `python detect_pies.py --help`

## Contact
For any questions about (running) the system, feel free to contact me at hessel.haagsma@rug.nl
