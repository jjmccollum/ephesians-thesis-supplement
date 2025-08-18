#!/usr/bin/env python3

import argparse
import re
from lxml import etree as et

"""
XML namespaces
"""
xml_ns = "http://www.w3.org/XML/1998/namespace"
tei_ns = "http://www.tei-c.org/ns/1.0"

"""
Gregory-Aland witness siglum regex pattern
"""
witness_pattern = re.compile(r"^[LP]*\d+S*")

"""
Given a witness siglum and lists of suffixes,
returns the base siglum of the witness, stripped of all suffixes, and a list of its suffixes in the order they occur
"""
def parse_wit(wit, suffixes):
    base_wit = wit
    wit_suffixes = []
    while (True):
        suffix_found = False
        for suffix in suffixes:
            if base_wit.endswith(suffix):
                suffix_found = True
                base_wit = base_wit[:-len(suffix)]
                wit_suffixes = [suffix] + wit_suffixes
                break
        if not suffix_found:
            break
    return base_wit, wit_suffixes

"""
Returns a list of base witness sigla from the given XML tree's <listWit/> element.
"""
def get_list_wit(xml):
    #Populate a list of base sigla for witnesses:
    list_wit = []
    for witness in xml.xpath("/tei:TEI/tei:teiHeader/tei:fileDesc/tei:sourceDesc/tei:listWit/tei:witness", namespaces={"tei": tei_ns}):
        list_wit.append(witness.get("n"))
    return list_wit

"""
Returns a sorted copy of a list of witness sigla based on their indices in the wit_ind_map and suffix_ind_map dictionaries.
"""
def get_sorted_wits(wits, wit_ind_map, suffix_ind_map):
    # Proceed for each witness in the list:
    keys_by_wit = {}
    for wit in wits:
        wit_key_list = []
        if witness_pattern.match(wit) is not None:
            # If this witness is a manuscript, then decompose it into its base siglum and suffixes:
            base_wit, wit_suffixes = parse_wit(wit, suffix_ind_map.keys())
            # The first key is the index of the base witness:
            wit_key_list.append(wit_ind_map[base_wit])
            # The remaining keys are the respective indices of all suffixes appended to this witness:
            for wit_suffix in wit_suffixes:
                wit_key_list.append(suffix_ind_map[wit_suffix])
            # Convert this list to a tuple:
            wit_key = tuple(wit_key_list)
            keys_by_wit[wit] = wit_key
        else:
            # If this witness is not a manuscript, then don't decompose it:
            wit_key_list.append(wit_ind_map[wit])
            wit_key = tuple(wit_key_list)
            keys_by_wit[wit] = wit_key
    # Then sort the list by these keys in ascending order:
    return sorted(wits, key=lambda wit: keys_by_wit[wit])

"""
Given an <app/> element representing a variation unit, expand the "rell" witness to a list of all witnesses not explicitly cited under any reading
and sort the witness lists for each reading based on the witnesses' indices in the wit_ind_map and suffix_ind_map dictionaries.
The <app/> element is modified in place.
"""
def convert_app(xml, wit_ind_map, suffix_ind_map):
    app_id = xml.get("{%s}id" % xml_ns)
    # First, populate a set of all base witnesses whose sigla are encountered (with or without suffixes) in any reading:
    base_wits_cited = set()
    for rdg in xml.xpath(".//tei:rdg|.//tei:witDetail", namespaces={"tei": tei_ns}):
        for wit in rdg.get("wit").split():
            # The "rell" siglum is not really a witness, so ignore it:
            if wit == "rell":
                continue
            if witness_pattern.match(wit) is not None:
                # If this witness is a manuscript, then decompose it into its base siglum and suffixes:
                base_wit, suffixes = parse_wit(wit, suffix_ind_map.keys())
                base_wits_cited.add(base_wit)
            else:
                # If this witness is not a manuscript, then add it as-is:
                base_wits_cited.add(wit)
    # Next, expand the "rell" siglum to a sequence of all uncited witnesses and sort all witness sequences:
    uncited_wits_str = ' '.join([wit for wit in wit_ind_map.keys() if wit not in base_wits_cited])
    for rdg in xml.xpath(".//tei:rdg|.//tei:witDetail", namespaces={"tei": tei_ns}):
        rdg_n = rdg.get("n")
        rdg.attrib["wit"] = rdg.get("wit").replace("rell", uncited_wits_str)
        # Try to sort the witness list:
        rdg_wits = rdg.get("wit").split()
        try:
            rdg.attrib["wit"] = ' '.join(get_sorted_wits(rdg_wits, wit_ind_map, suffix_ind_map))
        except Exception as e:
            print("Error encountered in variation unit %s, reading %s: %s" % (app_id, rdg_n, e))
    return

"""
Given an XML tree of a TEI collation, convert its negative apparatuses to positive ones in place.
The user-specified list of suffixes is used for extracting base witness sigla and sorting witness lists.
"""
def convert_negative_to_positive_apparatus(xml, suffixes):
    # First, populate maps of base witness sigla and suffixes to their indices in the <listWit/> element and user-specified suffix list, respectively:
    list_wit = get_list_wit(xml)
    wit_ind_map = {}
    for i, base_wit in enumerate(list_wit):
        wit_ind_map[base_wit] = i
    suffix_ind_map = {}
    for i, suffix in enumerate(suffixes):
        suffix_ind_map[suffix] = i
    # Then update each <app/> element in place:
    for app in xml.xpath('//tei:app', namespaces={'tei': tei_ns}):
        convert_app(app, wit_ind_map, suffix_ind_map)
    return

"""
Entry point to the script. Parses command-line arguments and calls the core functions.
"""
def main():
    parser = argparse.ArgumentParser(description='Converts the negative apparatuses in the given TEI XML collation file to positive apparatuses, listing all witnesses in sorted order under their respective readings, and writes the resulting XML tree to the given output.')
    parser.add_argument('-s', metavar='suffix', type=str, action='append', help='Suffixes for first hand, main text, corrector, alternate text, and multiple attestation (e.g., *, T, C, C1, C2, C3, A, A1, A2, K, K1, K2, /1, /2). Subwitnesses of the same base witness will be sorted according to the specified order of their suffixes. If more than one suffix is used, this argument can be specified multiple times.')
    parser.add_argument('-o', metavar='output', type=str, help='Filename for the TEI XML output containing positive apparatuses (if none is specified, then the output is written to the console).')
    parser.add_argument('input', type=str, help='TEI XML collation file containing negative apparatuses.')
    args = parser.parse_args()
    # Parse the optional arguments:
    output_addr = args.o
    suffixes = [] if args.s is None else args.s
    # Parse the positional arguments:
    input_addr = args.input
    # Parse the input XML document:
    xml = et.parse(input_addr)
    # Convert it in place:
    convert_negative_to_positive_apparatus(xml, suffixes)
    #Then write the XML of this variation unit to output:
    if output_addr is None:
        print(et.tostring(xml, encoding='utf-8', xml_declaration=True, pretty_print=True))
    else:
        xml.write(output_addr, encoding='utf-8', xml_declaration=True, pretty_print=True)
    exit(0)

if __name__=="__main__":
    main()