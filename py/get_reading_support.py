#!/usr/bin/env python3

import argparse
from lxml import etree as et  # for reading TEI XML inputs

"""
XML namespaces
"""
xml_ns = "http://www.w3.org/XML/1998/namespace"
tei_ns = "http://www.tei-c.org/ns/1.0"

"""
Map from significant witnesses to their LaTeX macros
"""
sigla_to_latex = {
    "P46": "P46",
    "01": "01",
    "01C1": "01C1",
    "01C2a": "01C2a",
    "01C2b": "01C2b",
    "01C2": "01C2",
    "02": "02",
    "03": "03",
    "03C1": "03C1",
    "03C2": "03C2",
    "06": "06",
    "06C1": "06C1",
    "06C2": "06C2",
    "012": "012",
    "025": "025",
    "044": "044",
    "075": "075",
    "0150": "0150",
    "0278": "0278",
    "6": "6",
    "33": "33",
    "81": "81",
    "94": "94",
    "256": "256",
    "263": "263",
    "424C1": "414C1",
    "442": "442",
    "606": "606",
    "1175": "1175",
    "1398": "1398",
    "1678": "1678",
    "1739": "1739",
    "1834": "1834",
    "1840": "1840",
    "1881": "1881",
    "1908": "1908",
    "1910": "1910",
    "1962": "1962",
    "1985": "1985",
    "1987": "1987",
    "1991": "1991",
    "2008": "2008",
    "2011": "2011",
    "2464": "2464",
    "2492": "2492",
    "2576": "2576",
    "2805": "2805",
    "VL61": "VL61",
    "VL75": "VL75",
    "VL77": "VL77",
    "VL89": "VL89",
    "vgcl": "\\Vulgate{cl}",
    "vgww": "\\Vulgate{ww}",
    "vgst": "\\Vulgate{st}",
    "syrp": "\\Syriac{p}",
    "syrh": "\\Syriac{h}",
    "syrhmg": "\\Syriac{h mg}",
    "copsa": "\\Coptic{sa}",
    "copbo": "\\Coptic{bo}",
    "gothA": "\\Gothic{A}",
    "gothB": "\\Gothic{B}",
    "Ambrosiaster": "\\Ambrosiaster{}",
    "Chrysostom": "\\Chrysostom{}",
    "CyrilOfAlexandria": "\\CyrilOfAlexandria{}",
    "Ephrem": "\\Ephrem{}",
    "Jerome": "\\Jerome{}",
    "MariusVictorinus": "\\MariusVictorinus{}",
    "Origen": "\\Origen{}",
    "Pelagius": "\\Pelagius{}",
    "TheodoreOfMopsuestia": "\\TheodoreOfMopsuestia{}",
    "Theodoret": "\\Theodoret{}",
    "NA28": "\\NestleAland{28}",
    "NA28mg": "\\NestleAland{28 mg}",
    "RP": "\\RobinsonPierpont{}",
    "RPmg": "\\RobinsonPierpont{mg}",
    "SBL": "\\Sbl{}",
    "SBLmg": "\\Sbl{mg}",
    "TH": "\\TyndaleHouse{}",
    "WH": "\\WestcottHort{}",
    "WHmg": "\\WestcottHort{mg}",
}

def is_manuscript(wit):
    """
    Given a base witness siglum, return a flag indicating whether or not the witness represents a manuscript.
    """
    if wit == "NA28":
        return False
    last_character = wit[-1]
    if last_character in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
        return True
    if wit in ["gothA", "gothB"]:
        return True
    return False

def get_base_wit(wit, siglum_set):
    """
    Given a witness siglum and a set of target sigla,
    strips the input siglum's final character until the resulting siglum matches one in the target set 
    or until no more characters can be stripped.
    """
    base_wit = wit
    while len(base_wit) > 0:
        if base_wit in siglum_set:
            return base_wit
        base_wit = base_wit[:-1]
    return wit

def get_list_wit(xml):
    """
    Given an XML tree representing a TEI collation, returns a list of base sigla for collated witnesses.
    """
    list_wit = []
    for witness in xml.xpath("//tei:witness", namespaces={"tei": tei_ns}):
        witness_n = witness.get("n")
        list_wit.append(witness_n)
    return list_wit

def get_reading_support(xml, target_app_id, target_rdg_n, all_witnesses=False):
    """
    Given an XML tree representing a collation, a variation unit ID, and a reading number,
    returns a LaTeX string of witnesses among the sigla in the sigla_to_latex dictionary that support that reading (or any of its subvariants).
    Optionally, a flag can be specified indicating whether all witnesses should be included rather than the default significant subset in the sigla_to_latex subset.
    """
    reading_support = []
    # First, populate a set of base witness sigla from the listWit element:
    list_wit = get_list_wit(xml)
    base_sigla = set(list_wit)
    index_by_wit = {wit: i for i, wit in enumerate(list_wit)}
    subreading_mask_by_wit = {}
    # The non-substantive reading types are hardcoded for convenience:
    trivial_reading_types = set(["reconstructed", "defective", "orthographic", "subreading"])
    subreading_code_by_reading_type = {"reconstructed": 1, "defective": 2, "orthographic": 4, "subreading": 8}
    format_by_subreading_mask = ["{}", "{}V", "{}f", "{}fV", "{}r", "{}rV", "{}rf", "{}rfV", "({})", "({}V)", "({}f)", "({}fV)", "({}r)", "({}rV)", "({}rf)", "({}rfV)"]
    # Proceed through all readings in the variation unit, and start processing when we reach the one matching the specified number:
    found_substantive_rdg = False
    subreading_mask = 0 # the mask of all subreading codes currently under consideration; it is used to account for hierarchical combinations, like defective forms of orthographic subvariants
    subreading_code = 0 # the subreading code of the current reading under consideration
    # Then locate the target variation unit:
    for app in xml.xpath(".//tei:app", namespaces={"tei": tei_ns}):
        app_id = app.get("{%s}id" % xml_ns)
        if app_id != target_app_id:
            continue
        # Then proceed for every substantive reading in this variation unit:
        for rdg in app.xpath(".//tei:rdg", namespaces={"tei": tei_ns}):
            rdg_n = rdg.get("n")
            rdg_type = rdg.get("type")
            # Check if this is a substantive reading:
            if rdg_type is None or rdg_type not in trivial_reading_types:
                # If it is, then check if it is the target reading:
                if rdg_n == target_rdg_n:
                    # If it is, then set the processing flag to true and start processing its supporting witnesses:
                    found_substantive_rdg = True
                    subreading_code = 0
                    subreading_mask = 0
                    wits = rdg.get("wit").split()
                    for wit in wits:
                        base_wit = get_base_wit(wit, base_sigla)
                        if base_wit in sigla_to_latex or all_witnesses:
                            reading_support.append(wit)
                            subreading_mask_by_wit[wit] = subreading_mask
                else:
                    # If it is not, then set the processing flag to false and move on:
                    found_substantive_rdg = False
                    subreading_code = 0
                    subreading_mask = 0
                    continue
            else:
                # If it is not, then check whether the processing flag is on or off:
                if found_substantive_rdg:
                    # If it is on, then conditionally update the current subreading mask:
                    if subreading_code_by_reading_type[rdg_type] > subreading_code:
                        # If the current subreading code refers to a more substantive subreading type than the previous one did,
                        # then start over with the current subreading code:
                        subreading_mask = subreading_code_by_reading_type[rdg_type]
                    else:
                        # If the current subreading code refers to the same subreading type as the previous one 
                        # or a less substantive subreading type than the previous one,
                        # then this subreading modifies the parent subreading:
                        subreading_mask |= subreading_code_by_reading_type[rdg_type]
                    # Then set the current subreading code:
                    subreading_code = subreading_code_by_reading_type[rdg_type]
                    # Then process its supporting witnesses:
                    wits = rdg.get("wit").split()
                    for wit in wits:
                        base_wit = get_base_wit(wit, base_sigla)
                        if base_wit in sigla_to_latex or all_witnesses:
                            reading_support.append(wit)
                            if is_manuscript(base_wit):
                                subreading_mask_by_wit[wit] = subreading_mask
                            else:
                                # Non-manuscript witnesses, like versions, fathers, and editions, are always treated as having substantive readings:
                                subreading_mask_by_wit[wit] = 0
                else:
                    # If it is off, then move on:
                    continue
    # Finally, sort the witnesses by their base siglum indices and reformat them:
    reading_support = sorted(reading_support, key=lambda wit: index_by_wit[get_base_wit(wit, base_sigla)])
    formatted_reading_support = [format_by_subreading_mask[subreading_mask_by_wit[wit]].format(wit) for wit in reading_support]
    # Then convert this list to a LaTeX string:
    latex_string = ""
    for i in range(len(reading_support)):
        wit = reading_support[i]
        if is_manuscript(get_base_wit(wit, base_sigla)):
            latex_string += formatted_reading_support[i]
        else:
            latex_string += sigla_to_latex[get_base_wit(wit, base_sigla)] if get_base_wit(wit, base_sigla) in sigla_to_latex else get_base_wit(wit, base_sigla)
        latex_string += " "
    return latex_string

"""
Entry point to the script. Parses command-line arguments and calls the core functions.
"""
def main():
    parser = argparse.ArgumentParser(usage="get_reading_support.py [-h] [--all] collation app_id rdg_n", description="Returns a LaTeX string representing the support for a specified reading (and all of its subvariants) among a selected set of witnesses at a specified variation unit.")
    parser.add_argument("collation", metavar="collation", type=str, help="Address of collation file.")
    parser.add_argument("app_id", metavar="app_id", type=str, help="Variation unit ID.")
    parser.add_argument("rdg_n", metavar="rdg_n", type=str, help="Substantive reading number.")
    parser.add_argument("--all", "-a", action="store_true", help="If specified, include all witnesses rather than the default significant subset.")
    args = parser.parse_args()
    # Parse the positional arguments:
    collation_addr = args.collation
    app_id = args.app_id
    rdg_n = args.rdg_n
    # Parse the optional arguments:
    all_witnesses = args.all
    # Parse the input XML document:
    xml = et.parse(collation_addr)
    # Then get the output string:
    print(get_reading_support(xml, app_id, rdg_n, all_witnesses))

if __name__=="__main__":
    main()