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
    parser = argparse.ArgumentParser(description="Writes the contents of all lem elements in the specified TEI XML input to the specified output file.")
    parser.add_argument("input", type=str, help="TEI XML collation file")
    parser.add_argument("output", type=str, help="Output file")
    args = parser.parse_args()
    # Parse the positional arguments:
    input_addr = args.input
    output_addr = args.output
    # Parse the input XML document:
    xml = et.parse(input_addr)
    # Open the output file:
    with open(output_addr, "w", encoding="utf-8") as f:
        # Then proceed through all app elements:
        for w in xml.xpath("//tei:body/tei:milestone|//tei:app/tei:lem/tei:w|//tei:app/tei:lem/tei:milestone", namespaces={"tei": tei_ns}):
            if "milestone" in w.tag:
                if w.get("unit") == "chapter":
                    f.write(w.get("n").split("K")[1] + ":")
                elif w.get("unit") == "verse":
                    f.write(w.get("n").split("V")[1] + " ")
            else:
                f.write(w.text + " ")
    exit(0)

if __name__=="__main__":
    main()