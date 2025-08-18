#!/usr/bin/env python3

import argparse
from lxml import etree as et

"""
XML namespaces
"""
xml_ns = "http://www.w3.org/XML/1998/namespace"
tei_ns = "http://www.tei-c.org/ns/1.0"

"""
Entry point to the script. Parses command-line arguments and calls the core functions.
"""
def main():
    parser = argparse.ArgumentParser(description="Extracts manuscript witness elements from the specified collation file and typesets them in a LaTeX table.")
    parser.add_argument("collation", type=str, help="Address of collation file.")
    parser.add_argument("output", type=str, help="Filename for the output .tex file.")
    args = parser.parse_args()
    # Parse the positional arguments:
    collation_addr = args.collation
    output_addr = args.output
    # Parse the collation document:
    collation = et.parse(collation_addr)
    # Initialize the LaTeX output string and fill it by parsing all manuscript witness elements:
    latex = ""
    # Open the environments:
    latex += "\\begin{center}\n"
    latex += "\t\\begin{longtable}{p{0.1\\textwidth} p{0.1\\textwidth} p{0.2\\textwidth} p{0.5\\textwidth}}\n"
    # Then add the caption and label:
    latex += "\t\t\\caption[Details for Greek and Latin manuscripts collated in this study]{Details for Greek and Latin manuscripts collated in this study. Greek manuscripts are identified with Gregory-Aland (GA) numbers and Latin manuscripts with Beuron numbers}\n"
    latex += "\t\t\\label{tab:materials-manuscripts}\\\\\n"
    # Then add the header lines:
    latex += "\t\t\\emph{Siglum} & \\emph{Alt. Siglum} & \\emph{Date} & \emph{Description}\\\\\n"
    latex += "\t\t\\hline\n"
    latex += "\t\t\\endfirsthead\n"
    latex += "\t\t\\emph{Siglum} & \\emph{Alt. Siglum} & \\emph{Date} & \emph{Description}\\\\\n"
    latex += "\t\t\\hline\n"
    latex += "\t\t\\endhead\n"
    # Then proceed for each witness in the witness list:
    for witness in collation.xpath("//tei:witness", namespaces={"tei": tei_ns}):
        # Skip any witness that is not a standard manuscript, commentary, or lectionary
        if witness.get("type") is not None and witness.get("type") not in ["commentary", "lectionary"]:
            continue
        # Get the witness's number, siglum, bibliographic information, and date range: 
        witness_number = witness.get("n") if witness.get("n") is not None else ""
        witness_siglum = ""
        witness_abbr = witness.find(".//tei:abbr", namespaces={"tei": tei_ns})
        if witness_abbr is not None:
            witness_siglum = witness_abbr.text
        witness_bibliography = ""
        witness_ms_identifier = witness.find(".//tei:msIdentifier", namespaces={"tei": tei_ns})
        if witness_ms_identifier is not None:
            witness_settlement = witness_ms_identifier.find(".//tei:settlement", namespaces={"tei": tei_ns})
            if witness_settlement is not None:
                witness_bibliography += witness_settlement.text + ": "
            witness_repository = witness_ms_identifier.find(".//tei:repository", namespaces={"tei": tei_ns})
            if witness_repository is not None:
                witness_bibliography += witness_repository.text + ", "
            witness_idno = witness_ms_identifier.find(".//tei:idno", namespaces={"tei": tei_ns})
            if witness_idno is not None:
                witness_bibliography += witness_idno.text + "  " # 2 blank spaces added so they can be truncated next
        if len(witness_bibliography) > 1:
            witness_bibliography = witness_bibliography[:-2]
        witness_date_range = ""
        witness_orig_date = witness.find(".//tei:origDate", namespaces={"tei": tei_ns})
        if witness_orig_date is not None:
            if witness_orig_date.get("when") is not None:
                witness_date_range += witness_orig_date.get("when")
            elif witness_orig_date.get("notBefore") is not None and witness_orig_date.get("notAfter") is not None:
                witness_date_range += witness_orig_date.get("notBefore") + "\u2013" + witness_orig_date.get("notAfter")
        # Then add a row to the table for this witness:
        latex += "\t\t%s & %s & %s & %s\\\\\n" % (witness_number, witness_siglum, witness_date_range, witness_bibliography)
    # Close the environments:
    latex += "\t\\end{longtable}\n"
    latex += "\\end{center}\n"
    with open(output_addr, "w") as f:
        f.write(latex)
    exit(0)

if __name__=="__main__":
    main()