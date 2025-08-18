#!/usr/bin/env python3

import argparse
from lxml import etree as et

"""
XML namespaces
"""
xml_ns = "http://www.w3.org/XML/1998/namespace"
tei_ns = "http://www.tei-c.org/ns/1.0"

"""
Given an XML tree of a TEI collation, checks all witDetail elements with type "ambiguous" and reports if their numbers do not match with their target attributes.
"""
def check_ambiguous(xml):
    # Proceed for every variation unit:
    for app in xml.xpath("//tei:app", namespaces={"tei": tei_ns}):
        app_id = app.get("{%s}id" % xml_ns)
        # Then update each ambiguous rdg element in place:
        for wit_detail in app.xpath('.//tei:witDetail[@type="ambiguous"]', namespaces={'tei': tei_ns}):
            # Retrieve its target readings from its n attribute:
            rdg_id = wit_detail.get("n")
            if rdg_id is None:
                print("In variation unit %s, an ambiguous reading is lacking a number." % (app_id))
                continue
            target_rdgs_from_id = rdg_id.strip("W").split("-")[0].split("/")
            # Get its target attribute:
            target_rdgs = [] if wit_detail.get("target") is None else wit_detail.get("target").split()
            # Convert any IDs to short-form reading numbers:
            for i in range(len(target_rdgs)):
                if target_rdgs[i].startswith("#"):
                    target_rdgs[i] = target_rdgs[i].split("R")[1]
            # If it contains any certainty elements, record their targets:
            certainty_rdgs = list(target_rdgs)
            if len(wit_detail.xpath('.//tei:certainty', namespaces={'tei': tei_ns})) > 0:
                certainty_rdgs = []
                for certainty in wit_detail.xpath('.//tei:certainty', namespaces={'tei': tei_ns}):
                    certainty_rdg = certainty.get("target")
                    if certainty_rdg is None:
                        continue
                    if certainty_rdg.startswith("#"):
                        certainty_rdg = certainty_rdg.split("R")[1]
                    certainty_rdgs.append(certainty_rdg)
            # If any of these lists do not agree, then report this:
            if target_rdgs_from_id != target_rdgs:
                print("In variation unit %s, ambiguous reading %s has target=\"%s\"." % (app_id, rdg_id, " ".join(target_rdgs)))
            elif target_rdgs_from_id != certainty_rdgs:
                print("In variation unit %s, ambiguous reading %s has certainty elements with targets %s." % (app_id, rdg_id, " ".join(certainty_rdgs)))
    return

"""
Entry point to the script. Parses command-line arguments and calls the core functions.
"""
def main():
    parser = argparse.ArgumentParser(description='Checks all witDetail elements with type "ambiguous" and reports if their numbers do not match with their target attributes.')
    parser.add_argument('input', type=str, help='TEI XML collation file to check.')
    args = parser.parse_args()
    # Parse the positional arguments:
    input_addr = args.input
    # Parse the input XML document:
    xml = et.parse(input_addr)
    # Then check it:
    check_ambiguous(xml)
    exit(0)

if __name__=="__main__":
    main()