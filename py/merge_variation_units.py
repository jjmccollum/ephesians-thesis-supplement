#!/usr/bin/env python3

import argparse
from lxml import etree as et
from typing import List
import copy
import time

"""
XML namespaces
"""
xml_ns = "http://www.w3.org/XML/1998/namespace"
tei_ns = "http://www.tei-c.org/ns/1.0"

"""
Constants
"""
LAC_SYMBOL = "Z"

class Collation:
    """Base class for storing TEI XML collation data internally.

    This corresponds to the entire XML tree, rooted at the TEI element of the collation.

    Attributes:
        witnesses: A list of base witness sigla contained in this Collation.
        witness_index_by_id: A dictionary mapping base witness ID strings to their int indices in the witnesses list.
        variation_units: A list of lxml.etree.Element instances corresponding to the <app> elements with the variation unit IDs input to this Collation.
        reading_to_index_maps: A list of dictionaries mapping reading numbers to their int indices in the order they appear, with one dictionary for each variation unit.
    """
    def __init__(self, xml: et.ElementTree, variation_units: List[str]):
        """Constructs a new Collation instance with the given settings.

        Args:
            xml: An lxml.etree.ElementTree representing an XML tree rooted at a TEI element.
            variation_units: A list of variation unit IDs.
        """
        self.witnesses = []
        self.witness_index_by_id = {}
        self.variation_units = []
        self.reading_to_index_maps = []
        print("Initializing collation...")
        t0 = time.time()
        self.parse_list_wit(xml)
        self.parse_apps(xml, variation_units)
        t1 = time.time()
        print("Total time to initialize collation: %0.4fs." % (t1 - t0))

    def get_base_wit(self, wit: str):
            """Given a witness siglum, strips its final character until the siglum matches one in the witness list 
            or until no more characters can be stripped.

            Args:
                wit: A string representing a witness siglum, potentially including suffixes to be stripped.

            Returns:
                The base witness siglum, stripped of all suffixes.
            """
            base_wit = wit
            while len(base_wit) > 0:
                if base_wit in self.witness_index_by_id:
                    return base_wit
                base_wit = base_wit[:-1]
            # If we get here, then all possible manuscript suffixes have been stripped, and the resulting siglum does not correspond to a siglum in the witness list:
            return base_wit

    def parse_list_wit(self, xml: et.ElementTree):
        """Given an XML tree for a collation, populates its list of witnesses from its listWit element.
        If the XML tree does not contain a listWit element, then a ParsingException is thrown listing all distinct witness sigla encountered in the collation.

        Args:
            xml: An lxml.etree.ElementTree representing an XML tree rooted at a TEI element.
        """
        print("Parsing witness list...")
        t0 = time.time()
        self.witnesses = []
        self.witness_index_by_id = {}
        list_wits = xml.xpath("/tei:TEI//tei:listWit", namespaces={"tei": tei_ns})
        list_wit = list_wits[0]
        for witness in list_wit.xpath("./tei:witness", namespaces={"tei": tei_ns}):
            wit = ""
            if witness.get("{%s}id" % xml_ns) is not None:
                wit = witness.get("{%s}id" % xml_ns)
            elif witness.get("n") is not None:
                wit = witness.get("n")
            else:
                wit = witness.text
            self.witness_index_by_id[wit] = len(self.witnesses)
            self.witnesses.append(wit)
        t1 = time.time()
        print("Finished processing %d witnesses in %0.4fs." % (len(self.witnesses), t1 - t0))
        return

    def parse_apps(self, xml: et.ElementTree, target_variation_units: List[str]):
        """Given an XML tree for a collation, populates this Collation's list of variation unit lxml.etree.Element instances 
        from the elements whose IDs are specified in the given list
        and populates this Collation's list of dictionaries mapping reading IDs to integer indices.

        Args:
            xml: An lxml.etree.ElementTree representing an XML tree rooted at a TEI element.
            variation_units: A list of variation unit IDs.
        """
        print("Parsing variation units...")
        t0 = time.time()
        for j, app in enumerate(xml.xpath("//tei:app", namespaces={"tei": tei_ns})):
            app_id = ""
            if app.get("{%s}id" % xml_ns) is not None:
                app_id = app.get("{%s}id" % xml_ns)
            elif app.get("n") is not None:
                app_id = app.get("n")
            # Skip any variation units not in the target list:
            if app_id not in target_variation_units:
                continue
            # Otherwise, add the XML element for this variation to this Collation's list:
            self.variation_units.append(app)
            # Then populate its map of reading IDs to indices:
            reading_to_index_map = {}
            for k, rdg in enumerate(app.xpath(".//tei:rdg|.//tei:witDetail", namespaces={"tei": tei_ns})):
                rdg_id = ""
                if rdg.get("{%s}id" % xml_ns) is not None:
                    rdg_id = rdg.get("{%s}id" % xml_ns)
                elif rdg.get("n") is not None:
                    rdg_id = rdg.get("n")
                reading_to_index_map[rdg_id] = k
            # If there is no entry for lacunae already, then add one:
            if LAC_SYMBOL not in reading_to_index_map:
                reading_to_index_map[LAC_SYMBOL] = len(reading_to_index_map)
            self.reading_to_index_maps.append(reading_to_index_map)
        t1 = time.time()
        print("Finished processing %d variation units in %0.4fs." % (len(self.variation_units), t1 - t0))
        return

    def merge_variation_units(self):
        """
        Merges the variant readings in this variation unit and returns the resulting variation unit.

        Returns:
            An lxml.etree.ElementTree containing a single <app> element merging this Collation's variation units.
        """
        # Populate a list of variation unit IDs (to use later):
        variation_unit_ids = []
        for variation_unit in self.variation_units:
            app_id = ""
            if variation_unit.get("{%s}id" % xml_ns) is not None:
                app_id = variation_unit.get("{%s}id" % xml_ns)
            elif variation_unit.get("n") is not None:
                app_id = variation_unit.get("n")
            variation_unit_ids.append(app_id)
        # Populate a dictionary of suffixed witness sigla sets, indexed by base siglum:
        sigla_by_base_witness = {}
        for wit in self.witnesses:
            sigla_by_base_witness[wit] = set()
        for variation_unit in self.variation_units:
            for rdg in variation_unit.xpath(".//tei:rdg|.//tei:witDetail", namespaces={"tei": tei_ns}):
                wits = rdg.get("wit").replace("#", "").split()
                for wit in wits:
                    base_wit = self.get_base_wit(wit)
                    if base_wit == "":
                        print("Encountered siglum %s with no corresponding base witness!" % wit)
                    if wit == base_wit:
                        continue
                    # If this witness siglum is a prefix of any other suffixed witness siglum, then don't add it:
                    is_prefix = False
                    for siglum in sigla_by_base_witness[base_wit]:
                        if wit in siglum and siglum != wit:
                            is_prefix = True
                            break
                    if is_prefix:
                        continue
                    # Otherwise, remove any other suffixed witness sigla that are prefixes of this one:
                    for siglum in sigla_by_base_witness[base_wit]:
                        if siglum in wit and siglum != wit:
                            sigla_by_base_witness[base_wit].remove(siglum)
                            break
                    # And then add this siglum:
                    sigla_by_base_witness[base_wit].add(wit)
        # Initialize a dictionary of variant reading lists, indexed by witness sigla:
        reading_lists_by_siglum = {}
        for base_wit in self.witnesses:
            # If this witness has no suffixed sigla in the variation units, then just populate an entry for the base siglum:
            if len(sigla_by_base_witness[base_wit]) == 0:
                reading_lists_by_siglum[base_wit] = [LAC_SYMBOL] * len(self.variation_units)
                continue
            # Otherwise, populate an entry for each of its suffixed sigla:
            for siglum in sigla_by_base_witness[base_wit]:
                reading_lists_by_siglum[siglum] = [LAC_SYMBOL] * len(self.variation_units)
                continue
        # Then populate this dictionary using the variant readings:
        for i, variation_unit in enumerate(self.variation_units):
            # Proceed for each reading:
            for rdg in variation_unit.xpath(".//tei:rdg|.//tei:witDetail", namespaces={"tei": tei_ns}):
                # Get this reading's ID:
                rdg_id = ""
                if rdg.get("{%s}id" % xml_ns) is not None:
                    rdg_id = rdg.get("{%s}id" % xml_ns)
                elif rdg.get("n") is not None:
                    rdg_id = rdg.get("n")
                # Then loop through its witness list:
                wits = rdg.get("wit").replace("#", "").split()
                for wit in wits:
                    # If this siglum has its own entry in the reading tuples dictionary, then set its reading entry here:
                    if wit in reading_lists_by_siglum:
                        reading_lists_by_siglum[wit][i] = rdg_id
                        continue
                    # Otherwise, populate an entry for each suffixed siglum for which this siglum is a prefix:
                    base_wit = self.get_base_wit(wit)
                    for siglum in sigla_by_base_witness[base_wit]:
                        if wit in siglum:
                            reading_lists_by_siglum[siglum][i] = rdg_id
                    continue
        # Next, populate a dictionary mapping the reading ID sequences to sorted lists of their witness sigla:
        wits_by_reading_sequence = {}
        for wit in reading_lists_by_siglum:
            rdg_sequence = ",".join(reading_lists_by_siglum[wit])
            if rdg_sequence not in wits_by_reading_sequence:
                wits_by_reading_sequence[rdg_sequence] = []
            wits_by_reading_sequence[rdg_sequence].append(wit)
        keys_by_wit = {}
        for i, wit in enumerate(self.witnesses):
            keys_by_wit[wit] = i
        for rdg_sequence in wits_by_reading_sequence:
            wits_by_reading_sequence[rdg_sequence] = sorted(wits_by_reading_sequence[rdg_sequence], key=lambda w: self.witness_index_by_id[self.get_base_wit(w)])
        # Next, populate a dictionary mapping each (variation unit ID, reading ID) tuple to an XML element:
        rdg_by_app_rdg = {}
        for i, variation_unit in enumerate(self.variation_units):
            app_id = variation_unit_ids[i]
            for rdg in variation_unit.xpath(".//tei:rdg|.//tei:witDetail", namespaces={"tei": tei_ns}):
                rdg_id = ""
                if rdg.get("{%s}id" % xml_ns) is not None:
                    rdg_id = rdg.get("{%s}id" % xml_ns)
                elif rdg.get("n") is not None:
                    rdg_id = rdg.get("n")
                rdg_by_app_rdg[(app_id, rdg_id)] = rdg
            # If there is no entry for lacunae at this unit, then create one:
            if (app_id, LAC_SYMBOL) not in rdg_by_app_rdg:
                wit_detail = et.Element("witDetail", nsmap={None: tei_ns, "xml": xml_ns})
                wit_detail.set("n", LAC_SYMBOL)
                wit_detail.set("type", "lac")
                rdg_by_app_rdg[(app_id, LAC_SYMBOL)] = wit_detail
        # Then generate a new <app> element containing the combined elements for each sequence of readings:
        app = et.Element("app", nsmap={None: tei_ns, "xml": xml_ns})
        app.text = "\n\t"
        # Sort the reading sequences lexicographically:
        rdg_sequences = sorted(list(wits_by_reading_sequence.keys()), key=lambda reading_sequence: [self.reading_to_index_maps[j][rdg_id] for j, rdg_id in enumerate(reading_sequence.split(","))])
        print(rdg_sequences)
        for rdg_sequence in rdg_sequences:
            merged_rdg = et.Element("rdg", nsmap={None: tei_ns})
            merged_rdg.text = "\n\t\t"
            merged_rdg.tail = "\n\t"
            merged_rdg.set("n", rdg_sequence)
            merged_rdg.set("wit", " ".join(wits_by_reading_sequence[rdg_sequence]))
            types = [] # the union of all types for the merged readings
            causes = [] # the union of all causes for the merged readings
            anas = [] # the union of all analytic tags for the merged readings
            langs = [] # the union of all languages for the merged readings
            rdg_ids = rdg_sequence.split(",")
            for i, rdg_id in enumerate(rdg_ids):
                variation_unit_id = variation_unit_ids[i]
                rdg = rdg_by_app_rdg[(variation_unit_id, rdg_id)]
                if rdg.get("type") is not None:
                    rdg_type = rdg.get("type")
                    if rdg_type not in types:
                        types.append(rdg_type)
                if rdg.get("cause") is not None:
                    rdg_cause = rdg.get("cause")
                    if rdg_cause not in causes:
                        causes.append(rdg_cause)
                if rdg.get("ana") is not None:
                    rdg_ana = rdg.get("ana")
                    if rdg_ana not in anas:
                        anas.append(rdg_ana)
                if rdg.get("{%s}lang" % xml_ns) is not None:
                    rdg_lang = rdg.get("{%s}lang" % xml_ns)
                    if rdg_lang not in langs:
                        langs.append(rdg_lang)
                # Add a <seg> element containing this reading's content:
                seg = et.Element("seg", nsmap={None: tei_ns})
                for child in rdg:
                    seg.append(copy.deepcopy(child))
                seg.text = rdg.text
                if len(seg) > 0:
                    seg.text = "\n\t\t\t"
                    seg[-1].tail = "\n\t\t"
                seg.tail = "\n\t\t"
                merged_rdg.append(seg)
            if len(merged_rdg) > 0:
                merged_rdg[-1].tail = "\n\t"
            # Then set the attributes of the merged reading element:
            if len(types) > 0:
                merged_rdg.set("type", " ".join(types))
            if len(causes) > 0:
                merged_rdg.set("cause", " ".join(causes))
            if len(anas) > 0:
                merged_rdg.set("ana", " ".join(anas))
            if len(langs) > 0:
                merged_rdg.set("{%s}lang" % xml_ns, " ".join(langs))
            app.append(merged_rdg)
        return app

"""
Entry point to the script. Parses command-line arguments and calls the core functions.
"""
def main():
    parser = argparse.ArgumentParser(description="Merges the given variation units in the given TEI XML collation file and writes the merged variation unit\"s XML tree to the given output.")
    parser.add_argument("-o", metavar="output", type=str, help="output filename (if none is specified, then the output is written to the console).")
    parser.add_argument("input", type=str, help="TEI XML collation file.")
    parser.add_argument("passages", metavar="variation_unit", type=str, nargs="+", help="IDs of the variation units to merge.")
    args = parser.parse_args()
    #Parse the optional arguments:
    output_addr = args.o
    #Parse the positional arguments:
    input_addr = args.input
    variation_units = args.passages
    #Parse the input XML document:
    parser = et.XMLParser(remove_blank_text=True)
    xml = et.parse(input_addr, parser=parser)
    # Then initialize a limited collation from this XML:
    coll = Collation(xml, variation_units)
    #Then get the merged variation unit:
    merged_vu = coll.merge_variation_units()
    #Then write the XML of this variation unit to output:
    if output_addr is None:
        print(et.tostring(merged_vu, encoding="utf-8", xml_declaration=True))
    else:
        tree = et.ElementTree(merged_vu)
        tree.write(output_addr, encoding="utf-8", xml_declaration=True)
    exit(0)

if __name__=="__main__":
    main()