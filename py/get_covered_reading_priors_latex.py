#!/usr/bin/env python3

import argparse
import string
import re
from lxml import etree as et

"""
XML namespaces
"""
xml_ns = "http://www.w3.org/XML/1998/namespace"
tei_ns = "http://www.tei-c.org/ns/1.0"

"""
Dictionary mapping intrinsic odds categories to their numerical values.
"""
odds_by_category = {
    "RatingA": 100.0,
    "RatingB": 31.622776601683793,
    "RatingC": 10.0,
    "RatingD": 3.1622776601683795,
    "EqualRating": 1.0
}

def is_covered_variation_unit(app):
    # Get this variation unit's intrinsic relation elements, if it has any:
    relations = app.xpath(".//tei:listRelation[@type=\"intrinsic\"]/tei:relation", namespaces={"tei": tei_ns})
    # If it has none, then this variation unit is not covered (since there is presumably no variation):
    if len(relations) == 0:
        return False
    # Otherwise, check if any of its intrinsic relation elements has an ana attribute with value "#DefaultRating", and report False if so:
    for relation in relations:
        ana = relation.get("ana") if relation.get("ana") is not None else ""
        if ana == "#DefaultRating":
            return False
    return True

def parse_variation_unit_label(vu_id):
    vu_label = vu_id
    vu_label = re.sub(r"B(\d+)", "Eph ", vu_label)
    vu_label = re.sub(r"K(\d+)", r"\1:", vu_label)
    vu_label = re.sub(r"V(\d+)", r"\1/", vu_label)
    vu_label = re.sub(r"U(\d+)", r"\1", vu_label)
    vu_label = vu_label.replace("-", "\u2013")
    return vu_label

def parse_reading_contents(rdg):
    text = ""
    # Proceed for all children of this reading element:
    for child in rdg:
        # Skip comments:
        if isinstance(child, et._Comment):
            continue
        # Determine what this element is:
        raw_tag = child.tag.replace("{%s}" % tei_ns, "")
        # If it is a word, then serialize its text:
        if raw_tag == "w":
            text += child.text if child.text is not None else ""
            text += child.tail if child.tail is not None else ""
            text += " "
        # If it is a reference, then serialize it:
        elif raw_tag == "ref":
            text += "\\emph{" + (parse_variation_unit_label(child.get("target").strip("#")) if child.get("target") is not None else "") + "}"
            text += child.tail if child.tail is not None else ""
            text += " "
    # Strip any whitespace from the end:
    text = text.strip()
    # If this text is empty, then it corresponds to an omission; typeset it accordingly:
    if text == "":
        text = "\u2013"
    # Otherwise, if this text does not contain emphasized references, then it consists entirely of Greek text; typeset it accordingly:
    elif "\\emph" not in text:
        text = "\\textgreek{" + text + "}"
    return text

def get_priors_by_reading_id(app):
    priors_by_reading_id = {}
    # First, populate an intrinsic relations dictionary with the intrinsic relations in this unit:
    intrinsic_relations = {}
    for relation in app.xpath(".//tei:listRelation[@type=\"intrinsic\"]/tei:relation", namespaces={"tei": tei_ns}):
        # Skip any relations without the necessary attributes:
        if relation.get("active") is None or relation.get("passive") is None or relation.get("ana") is None:
            continue
        # Get all of its attributes as lists:
        from_readings = relation.get("active").replace("#", "").split()
        to_readings = relation.get("passive").replace("#", "").split()
        intrinsic_category = relation.get("ana").replace("#", "").split()[0] # there shouldn't be more than one of these
        # For each pair of readings, assign them the specified category:
        for from_reading in from_readings:
            for to_reading in to_readings:
                pair = (from_reading, to_reading)
                intrinsic_relations[pair] = intrinsic_category
    # Then construct an adjacency list for efficient edge iteration:
    neighbors_by_source = {}
    for edge in intrinsic_relations:
        s = edge[0]
        t = edge[1]
        if s not in neighbors_by_source:
            neighbors_by_source[s] = []
        if t not in neighbors_by_source:
            neighbors_by_source[t] = []
        neighbors_by_source[s].append(t)
    # Next, identify all readings that are not targeted by any intrinsic odds relation:
    in_degree_by_reading = {}
    for edge in intrinsic_relations:
        s = edge[0]
        t = edge[1]
        if s not in in_degree_by_reading:
            in_degree_by_reading[s] = 0
        if t not in in_degree_by_reading:
            in_degree_by_reading[t] = 0
        in_degree_by_reading[t] += 1
    starting_nodes = [t for t in in_degree_by_reading if in_degree_by_reading[t] == 0]
    # Set the root frequencies for these readings to 1 (they will be normalized later):
    for starting_node in starting_nodes:
        priors_by_reading_id[starting_node] = 1.0
    # Next, set the frequencies for the remaining readings recursively using the adjacency list:
    def update_root_frequencies(s):
        for t in neighbors_by_source[s]:
            intrinsic_category = intrinsic_relations[(s, t)]
            odds = odds_by_category[intrinsic_category] if odds_by_category[intrinsic_category] is not None else 1.0
            priors_by_reading_id[t] = priors_by_reading_id[s] / odds
            update_root_frequencies(t)
        return
    for starting_node in starting_nodes:
        update_root_frequencies(starting_node)
    # Then normalize the entries of the dictionary so that they constitute a probability distribution:
    total_frequencies = sum(priors_by_reading_id.values())
    for k in priors_by_reading_id:
        priors_by_reading_id[k] = priors_by_reading_id[k] / total_frequencies
    return priors_by_reading_id

"""
Given an XML tree corresponding to a collation,
serialize the priors of all variation units without an intrinsic relation with ana="#DefaultRating"
as an extended LaTeX longtable.
"""
def get_covered_reading_priors_latex(xml):
    latex = ""
    # First, open the LaTeX environment for the table:
    latex += "\\begin{center}\n"
    latex += "\t\\begin{longtable}{A{0.5\\textwidth}|r}\n"
    # Add the caption and label:
    latex += "\t\t\\caption[Prior probabilities for readings covered in the commentary chapter and appendix]{Prior probabilities for readings covered in the commentary chapter and appendix.}\n"
    latex += "\t\t\\label{tab:commentary-readings-prior-probabilities}\\\\\n"
    latex += "\t\t\\emph{Reading} & \\emph{Prior}\\\\\n"
    latex += "\t\t\\hline\n"
    latex += "\t\t\\hline\n"
    latex += "\t\t\\endfirsthead\n"
    latex += "\t\t\\emph{Reading} & \\emph{Prior}\\\\\n"
    latex += "\t\t\\hline\n"
    latex += "\t\t\\hline\n"
    latex += "\t\t\\endhead\n"
    # The proceed for each variation unit in the collation:
    for app in xml.xpath(".//tei:app", namespaces={"tei": tei_ns}):
        # Parse the variation unit ID:
        vu_id = app.get("{%s}id" % xml_ns)
        # Check if this unit has been covered in the commentary, and skip it if not:
        if not is_covered_variation_unit(app):
            continue
        # Otherwise, populate a dictionary mapping the reading IDs to their prior probabilities:
        priors_by_reading_id = get_priors_by_reading_id(app)
        # Then add a header row for the variation unit and rows for all of its substantive readings:
        latex += "\t\t\\multicolumn{2}{c}{\\textbf{%s}}\\\\\n" % parse_variation_unit_label(vu_id)
        latex += "\t\t\\hline\n"
        latex += "\t\t\\hline\n"
        for rdg in app.xpath(".//tei:rdg", namespaces={"tei": tei_ns}):
            # Get each reading's number and ID attributes:
            rdg_n = rdg.get("n")
            rdg_id = rdg.get("{%s}id" % xml_ns) if rdg.get("{%s}id" % xml_ns) is not None else rdg_n
            # If this reading's ID is not in the priors dictionary, then skip it:
            if rdg_id not in priors_by_reading_id:
                continue
            # Otherwise, parse its text and retrieve its prior probability:
            rdg_text = parse_reading_contents(rdg)
            rdg_prior = priors_by_reading_id[rdg_id]
            # Then print its row:
            latex += "\t\t\\Rdg{%s}: %s & $%.3f\\%%$\\\\\n" % (string.ascii_lowercase[int(rdg_n) - 1], rdg_text, rdg_prior * 100)
            latex += "\t\t\\hline\n"
        latex += "\t\t\\hline\n"
    # Close the longtable environment:
    latex += "\t\\end{longtable}\n"
    # Close the center environment:
    latex += "\\end{center}"
    # Then return the LaTeX string:
    return latex

"""
Entry point to the script. Parses command-line arguments and calls the core functions.
"""
def main():
    parser = argparse.ArgumentParser(usage="get_root_reading_posteriors_latex.py [-h] collation", description="Returns a LaTeX string for a longtable enumerating the prior probabilities of readings in all variation units covered in the commentary.")
    parser.add_argument("collation", metavar="collation", type=str, help="Address of collation file.")
    args = parser.parse_args()
    # Parse the positional arguments:
    collation_addr = args.collation
    # Parse the input XML document:
    xml = et.parse(collation_addr)
    # Then get the output string:
    print(get_covered_reading_priors_latex(xml))

if __name__=="__main__":
    main()