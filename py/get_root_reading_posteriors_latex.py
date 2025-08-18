#!/usr/bin/env python3

import argparse
import string
import re
from lxml import etree as et
import yaml
from get_reading_support import get_reading_support

"""
Given an XML tree representing a collation, a dictionary mapping variation unit IDs to dictionaries of readings to dictionaries mapping the readings to their posterior probabilities,
serialize the dictionary for a specified variation unit ID as a LaTeX longtable.
"""
def get_root_reading_posteriors_latex(xml, posteriors_by_vu, app_id):
    latex = ""
    # Print an introductory sentence:
    vu_label = re.sub(r"B\d+", "", app_id)
    latex += "The posterior probabilities for readings based on sampled stemmata are given in Table \\ref{tab:%s-posterior-probabilities}.\n\n" % vu_label
    # Open the LaTeX environments:
    latex += "\\begin{center}\n"
    latex += "\t\\begin{longtable}{A{0.25\\textwidth}|A{0.5\\textwidth}|r}\n"
    # Then add the caption and label for the table:
    app_string = app_id
    app_string = re.sub(r"B(\d+)", "Eph ", app_string)
    app_string = re.sub(r"K(\d+)", r"\1:", app_string)
    app_string = re.sub(r"V(\d+)", r"\1/", app_string)
    app_string = re.sub(r"U(\d+)", r"\1", app_string)
    app_string = app_string.replace("-", "\u2013")
    latex += "\t\t\\caption[Reading posterior probabilities for %s]{Reading posterior probabilities for %s.}\n" % (app_string, app_string)
    latex += "\t\t\\label{tab:%s-posterior-probabilities}\\\\\n" % vu_label
    # Then add the header row:
    latex += "\t\tReading & Significant support & Posterior\\\\\n"
    latex += "\t\t\\hline\n"
    latex += "\t\t\\hline\n"
    # Sort the posteriors dictionary for this unit by value in descending order of posterior probability:
    posteriors_dict = posteriors_by_vu[app_id]
    reading_texts = [rdg for rdg in posteriors_dict.keys()]
    posteriors_by_reading_n = {i: v for i, v in enumerate(posteriors_dict.values())}
    posteriors_by_reading_n = dict(sorted(posteriors_by_reading_n.items(), key=lambda item: float(item[1]), reverse=True))
    # The populate the contents of the rows:
    for i, v in posteriors_by_reading_n.items():
        # First, get the alphabetical index of the reading:
        alphabetical_index = string.ascii_lowercase[i]
        # Then get the text of the reading, with underscores replaced with spaces and "om." replaced with "–", the significant support for the reading, and the posterior probability of that reading:
        rdg_text = reading_texts[i].replace("_", " ").replace("om.", "\u2013")
        support_str = get_reading_support(xml, app_id, str(i + 1))
        posterior = v
        # Then add the row:
        if v == 1.0:
            latex += "\t\t\\Rdg{%s}: \\textgreek{%s} & %s & $\\approx 100.000\\%%$" % (alphabetical_index, rdg_text, support_str.strip())
        elif v >= 1e-5:
            latex += "\t\t\\Rdg{%s}: \\textgreek{%s} & %s & $%.3f\\%%$" % (alphabetical_index, rdg_text, support_str.strip(), v * 100)
        else:
            latex += "\t\t\\Rdg{%s}: \\textgreek{%s} & %s & $< 0.001\\%%$" % (alphabetical_index, rdg_text, support_str.strip())
        if i != list(posteriors_by_reading_n.keys())[-1]:
            latex += "\\\\\n"
            latex += "\t\t\\hline\n"
        else:
            latex += "\n"
    # Close the longtable environment:
    latex += "\t\end{longtable}\n"
    # Close the center environment:
    latex += "\\end{center}"
    # Then return the LaTeX string:
    return latex

"""
Entry point to the script. Parses command-line arguments and calls the core functions.
"""
def main():
    parser = argparse.ArgumentParser(usage="get_root_reading_posteriors_latex.py [-h] collation app_id", description="Returns a LaTeX string for a longtable enumerating the posterior probabilities of readings in the specified variation unit.")
    parser.add_argument("collation", metavar="collation", type=str, help="Address of collation file.")
    parser.add_argument("posterior_file", metavar="posterior_file", type=str, help="Address of .yaml file containing the posterior probabilities of readings.")
    parser.add_argument("app_id", metavar="app_id", type=str, help="Variation unit ID.")
    args = parser.parse_args()
    # Parse the positional arguments:
    collation_file = args.collation
    posterior_file = args.posterior_file
    app_id = args.app_id
    # Parse the input documents:
    xml = et.parse(collation_file)
    posteriors_by_vu = {}
    with open(posterior_file, encoding="utf8") as f:
        posteriors_by_vu = yaml.safe_load(f)
    # Then get the output string:
    print(get_root_reading_posteriors_latex(xml, posteriors_by_vu, app_id))

if __name__=="__main__":
    main()