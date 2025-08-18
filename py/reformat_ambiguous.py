#!/usr/bin/env python3

import argparse
from lxml import etree as et

"""
XML namespaces
"""
xml_ns = "http://www.w3.org/XML/1998/namespace"
tei_ns = "http://www.tei-c.org/ns/1.0"

"""
Given an XML tree of a TEI collation, convert its rdg elements with type "ambiguous" to witDetail elements with the appropriate target values in place.
"""
def reformat_ambiguous(xml):
    # Then update each ambiguous rdg element in place:
    for rdg in xml.xpath('//tei:rdg[@type="ambiguous"]', namespaces={'tei': tei_ns}):
        # Retrieve its target readings from its n attribute:
        rdg_n = rdg.get("n")
        target_rdgs = rdg_n.strip("W").split("-")[0].split("/")
        # Add a target attribute with these readings:
        rdg.attrib["target"] = " ".join(target_rdgs)
        # Then change the tag of the element:
        rdg.tag = "{%s}witDetail" % tei_ns
    return

"""
Entry point to the script. Parses command-line arguments and calls the core functions.
"""
def main():
    parser = argparse.ArgumentParser(description='Reformat rdg elements with type "ambiguous", and writes the resulting XML tree to the given output.')
    parser.add_argument('-o', metavar='output', type=str, help='Filename for the TEI XML output containing positive apparatuses (if none is specified, then the output is written to the console).')
    parser.add_argument('input', type=str, help='TEI XML collation file to modify.')
    args = parser.parse_args()
    # Parse the optional arguments:
    output_addr = args.o
    # Parse the positional arguments:
    input_addr = args.input
    # Parse the input XML document:
    xml = et.parse(input_addr)
    # Convert it in place:
    reformat_ambiguous(xml)
    #Then write the XML of this variation unit to output:
    if output_addr is None:
        print(et.tostring(xml, encoding='utf-8', xml_declaration=True, pretty_print=True))
    else:
        xml.write(output_addr, encoding='utf-8', xml_declaration=True, pretty_print=True)
    exit(0)

if __name__=="__main__":
    main()