#!/usr/bin/env python3

import argparse
from lxml import etree as et

"""
XML namespaces
"""
xml_ns = "http://www.w3.org/XML/1998/namespace"
tei_ns = "http://www.tei-c.org/ns/1.0"

"""
Given a witness siglum and a set of base witness sigla,
returns the base siglum of the witness, stripped of all suffixes.
"""
def parse_wit(wit, list_wit_set):
    base_wit = wit
    while (len(base_wit) > 0 and base_wit not in list_wit_set):
        base_wit = base_wit[:-1]
    # If no base witness could be found, then reset the base witness to the specified witness:
    if len(base_wit) == 0:
        base_wit = wit
    return base_wit

"""
Given an XML tree of a TEI collation,
return a dictionary mapping each base witness to lists of its extant and lacunose variation units.
"""
def tabulate_extant(xml):
    # First, populate a list of base witness sigla from the listWit element:
    list_wit = []
    for witness in xml.xpath("//tei:witness", namespaces={"tei": tei_ns}):
        wit_id = witness.get("{%s}id" % xml_ns) if witness.get("{%s}id" % xml_ns) is not None else witness.get("n")
        list_wit.append(wit_id)
    # Then populate a set from this list:
    list_wit_set = set(list_wit)
    # Then initialize the dictionary to be populated:
    tabulations_by_witness = {}
    for wit in list_wit:
        tabulations_by_witness[wit] = {"extant": [], "lacunose": []}
    # Then populate it one variation unit at a time:
    variation_units = xml.xpath("//tei:app", namespaces={"tei": tei_ns})
    for variation_unit in variation_units:
        vu_id = variation_unit.get("{%s}id" % xml_ns) if variation_unit.get("{%s}id" % xml_ns) is not None else variation_unit.get("n")
        if variation_unit.get("from") is not None and variation_unit.get("to") is not None:
            if variation_unit.get("from") != variation_unit.get("to"):
                vu_id += "_" + variation_unit.get("from") + "_" + variation_unit.get("to")
            else:
                vu_id += "_" + variation_unit.get("from")
        for rdg in variation_unit.xpath(".//tei:rdg|.//tei:witDetail", namespaces={"tei": tei_ns}):
            rdg_id = rdg.get("n")
            # Skip any children with type="lac" and type="overlap":
            if rdg.get("type") in ["lac", "overlap"]:
                continue
            if rdg.get("wit") is None:
                print("WARNING: variation unit %s has a reading %s without a wit attribute!" % (vu_id, rdg_id))
                continue
            # Loop through the list of witnesses to this reading:
            wits = rdg.get("wit").split()
            for wit in wits:
                base_wit = wit.strip("#")
                base_wit = parse_wit(base_wit, list_wit_set)
                # If this base siglum does not correspond to a witness in the listWit, then skip it:
                if base_wit not in list_wit_set:
                    continue
                # Otherwise, it is extant here; if it does not already have this variation unit's ID as its latest entry, then add it to its extant list:
                if len(tabulations_by_witness[base_wit]["extant"]) == 0 or tabulations_by_witness[base_wit]["extant"][-1] != vu_id:
                    tabulations_by_witness[base_wit]["extant"].append(vu_id)
        # In a final pass, mark all witnesses that are extant in this unit as lacunose:
        for wit in list_wit:
            if len(tabulations_by_witness[wit]["extant"]) == 0 or tabulations_by_witness[wit]["extant"][-1] != vu_id:
                tabulations_by_witness[wit]["lacunose"].append(vu_id)
    return tabulations_by_witness

"""
Entry point to the script. Parses command-line arguments and calls the core functions.
"""
def main():
    parser = argparse.ArgumentParser(description="Tabulates the count and percentage of all variation units at which each witness in a collation is not lacunose.")
    parser.add_argument("--all-extant", action=argparse.BooleanOptionalAction, help="Enumerate all variation units where witnesses are extant.")
    parser.add_argument("--all-lacunose", action=argparse.BooleanOptionalAction, help="Enumerate all variation units where witnesses are lacunose.")
    parser.add_argument("-w", metavar="witnesses", type=str, action="append", help="Target witnesses whose tabulations are desired. This flag can be used multiple times to specify multiple target witnesses.")
    parser.add_argument("input", type=str, help="Input TEI XML collation file.")
    args = parser.parse_args()
    # Parse the optional arguments:
    all_extant = args.all_extant
    all_lacunose = args.all_lacunose
    target_wits = [] if args.w is None else args.w
    # Parse the positional arguments:
    input_addr = args.input
    # Parse the input XML document:
    xml = et.parse(input_addr)
    # Then make the tabulations:
    tabulations_by_witness = tabulate_extant(xml)
    # If no target witnesses were specified, then use the full list of witnesses:
    if len(target_wits) == 0:
        target_wits = list(tabulations_by_witness.keys())
    # Get the maximum siglum length for later:
    max_siglum_length = max(max([len(wit) for wit in target_wits]), len("witness"))
    if all_extant or all_lacunose:
        # If the verbose flag is set, then print out the extant and lacunose units for each target witness:
        for target_wit in target_wits:
            print("Witness: %s" % target_wit)
            if all_extant:
                print("    Extant:")
                for vu_id in tabulations_by_witness[target_wit]["extant"]:
                    print("        %s" % vu_id)
            if all_lacunose:
                print("    Lacunose:")
                for vu_id in tabulations_by_witness[target_wit]["lacunose"]:
                    print("        %s" % vu_id)
    else:
        # Otherwise, print out the count and proportion of lacunose readings for each target witness:
        print("Total variation units: %d" % (len(tabulations_by_witness[target_wits[0]]["extant"]) + len(tabulations_by_witness[target_wits[0]]["lacunose"])))
        print("Witness%sCount    Proportion" % (" "*(max_siglum_length-len("witness")+1)))
        for target_wit in target_wits:
            print("%s%s%s%d    %0.4f" % (target_wit, " "*(max_siglum_length-len(target_wit)+1), " "*(len("count")-len(tabulations_by_witness[target_wit]["extant"])), len(tabulations_by_witness[target_wit]["extant"]), len(tabulations_by_witness[target_wit]["extant"])/(len(tabulations_by_witness[target_wit]["extant"]) + len(tabulations_by_witness[target_wit]["lacunose"]))))
        exit(0)

if __name__=="__main__":
    main()