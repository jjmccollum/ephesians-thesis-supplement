#!/usr/bin/env python3

import argparse

"""
Entry point to the script. Parses command-line arguments and calls the core functions.
"""
def main():
    parser = argparse.ArgumentParser(description="Converts a biblical text (within a single verse) to a LaTeX string encoding its ECM word indices, starting at a given index. Punctuation is extracted from the end of each word and added after the LaTeX macro.")
    parser.add_argument("start", type=int, help="Starting word index for this text (should be an even number).")
    parser.add_argument("text", type=str, help="The text to index with ECM word indices. This should be specified between quotation marks. (Example: \"υπερ εμου ινα μοι δοθη λογος εν ανοιξει του στοματος μου εν παρρησια γνωρισαι το μυστηριον υπερ ου πρεσβευω εν αλυσει\")")
    args = parser.parse_args()
    # Parse the positional arguments:
    start = args.start
    text = args.text
    # Initialize a list of tokens that count as punctuation:
    punctuation = [',', '.', ';', ':', '?', '!', '\u0151', '\u0387', '\u00b7']
    # Initialize the word index to be incremented:
    i = start
    # Initialize the LaTeX output to be printed to the console:
    latex = ""
    # Add spaces after any em-dashes to ensure that the text is tokenized correctly:
    text = text.replace("\u0151", "\u0151 ")
    for t in text.split():
        w = t
        pc = ""
        while w[-1] in punctuation:
            pc = t[-1] + pc
            w = w[:-1]
        latex += "\\ecmword{%d}{%s}%s " % (i, w, pc)
        i += 2
    print(latex)
    exit(0)

if __name__=="__main__":
    main()