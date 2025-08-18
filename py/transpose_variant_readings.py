#!/usr/bin/env python3

import argparse
from lxml import etree as et

"""
XML namespaces
"""
xml_ns = "http://www.w3.org/XML/1998/namespace"
tei_ns = "http://www.tei-c.org/ns/1.0"

"""
Key function for sorting all elements in an app element.
An element's key is a tuple with 2 elements:
(1) the tag of the element (0 for lem, 1 for rdg, 2 for witDetail, 3 for note); and
(2) a tuple representing the number of the element, which varies for each type of element.
Any XML comments are assigned the key of their previous sibling.
"""
def rdg_key(xml):
    key_list = []
    # If this element is a comment, then set its key to the key of the element that precedes it:
    if isinstance(xml, et._Comment):
        if xml.getprevious() is not None:
            return rdg_key(xml.getprevious())
        else:
            return tuple([-1]) # any comment at the start of the app element should still be first
    # Otherwise, get the tag index of the element:
    raw_tag = xml.tag.replace("{%s}" % tei_ns, "")
    if raw_tag == "lem":
        key_list.append(0)
    if raw_tag == "rdg":
        key_list.append(1)
        n = xml.get("n")
        rdg_n_list = [0, 0, 0, 0, 0]
        for part in n.split("-"):
            if part[0] == 'v':
                rdg_n_list[4] = int(part.strip("v"))
            elif part[0] == 'f':
                rdg_n_list[3] = int(part.strip("f"))
            elif part[0] == 'o':
                rdg_n_list[2] = int(part.strip("o"))
            elif part[0] == 's':
                rdg_n_list[1] = int(part.strip("s"))
            else:
                rdg_n_list[0] = int(part)
        key_list += rdg_n_list
    elif raw_tag == "witDetail":
        key_list.append(2)
        # Include an initial value of 0 for ambiguities, 1 for overlaps, and 2 for lacunae:
        wit_detail_type = xml.get("type")
        if wit_detail_type == "ambiguous":
            key_list.append(0)
            for target_n in xml.get("target").split():
                key_list.append(int(target_n))
            if len(xml.get("n").split("-")) > 1:
                key_list.append(int(xml.get("n").split("-")[1]))
        elif wit_detail_type == "overlap":
            key_list.append(1)
        elif wit_detail_type == "lac":
            key_list.append(2)
    elif raw_tag == "note":
        key_list.append(3)
    return tuple(key_list)

"""
Key function for sorting all certainty elements in an ambiguous witDetail element.
The key is just the certainty element's target value.
"""
def certainty_key(xml):
    # If this element is a comment, then set its key to the key of the element that precedes it:
    if isinstance(xml, et._Comment):
        if xml.getprevious() is not None:
            return certainty_key(xml.getprevious())
        else:
            return -1 # any comment at the start of the app element should still be first
    return reading_reference_key(xml.get("target"))

"""
Key function for sorting all relation elements in a listRelation element.
The key is a tuple of tuples for the target's active and passive values.
"""
def relation_key(xml):
    # If this element is a comment, then set its key to the key of the element that precedes it:
    if isinstance(xml, et._Comment):
        if xml.getprevious() is not None:
            return relation_key(xml.getprevious())
        else:
            return tuple([tuple([-1]), tuple([-1])]) # any comment at the start of the app element should still be first
    # If this element represents a Byzantine assimilation transcriptional relation, then place it last:
    if xml.get("ana") is not None and xml.get("ana") == "#Byz":
        return tuple([tuple([999]), tuple([999])])
    # Otherwise, get the tuples for the active and passive targets:
    active_keys = [reading_reference_key(k) for k in xml.get("active").split()]
    passive_keys = [reading_reference_key(k) for k in xml.get("passive").split()]
    return tuple([tuple(active_keys), tuple(passive_keys)])

"""
Key function for sorting references to readings (e.g., in a target attribute).
The key is the reading number.
If the reference is to an XML ID, then only the last part is needed for sorting.
"""
def reading_reference_key(rdg_str):
    if rdg_str[0] == '#':
        return int(rdg_str.split("R")[1])
    else:
        return int(rdg_str)

"""
Relabel a lem element, given a dictionary mapping old indices to new indices.
For now, this function does nothing.
"""
def process_lem(xml, transposition_dict):
    return

"""
Relabel a rdg element, given a dictionary mapping old indices to new indices.
"""
def process_rdg(xml, transposition_dict):
    # Get the number of this reading, and change its first part:
    rdg_n = xml.get("n")
    rdg_n_parts = rdg_n.split("-")
    rdg_n_parts[0] = transposition_dict[rdg_n_parts[0]]
    xml.set("n", "-".join(rdg_n_parts))
    # If this reading has an XML ID, then replace the last part of the ID with the new reading number:
    if xml.get("{%s}id" % xml_ns) is not None:
        rdg_id = xml.get("{%s}id" % xml_ns)
        rdg_id_parts = rdg_id.split("R")
        rdg_id_parts[1] = xml.get("n")
        xml.set("{%s}id" % xml_ns, "R".join(rdg_id_parts))
    return

"""
Relabel a certainty element, given a dictionary mapping old indices to new indices.
"""
def process_certainty(xml, transposition_dict):
    target = xml.get("target")
    # If the target is a reference to an XML ID, then replace only the last part corresponding to the reading number:
    if target[0] == '#':
        target_parts = target.strip("#").split("R")
        target_parts[1] = transposition_dict[target_parts[1]]
        target = "#" + "R".join(target_parts)
    xml.set("target", transposition_dict[target])
    return

"""
Relabel a witDetail element, given a dictionary mapping old indices to new indices.
The witDetail's child certainty elements, if it has any, will be recursively relabeled and then sorted.
"""
def process_wit_detail(xml, transposition_dict):
    # Get the number of this witDetail, and change its first part:
    rdg_n = xml.get("n")
    rdg_n_parts = rdg_n.split("-")
    rdg_n_targets = rdg_n_parts[0].strip("W").split("/")
    for i, target in enumerate(rdg_n_targets):
        rdg_n_targets[i] = transposition_dict[target]
    rdg_n_targets = sorted(rdg_n_targets, key=reading_reference_key) # ensure that the targets in the reading number are sorted appropriately
    rdg_n_parts[0] = "W" + "/".join(rdg_n_targets)
    xml.set("n", "-".join(rdg_n_parts))
    # If this witDetail has an XML ID, then replace the last part of the ID with the new reading number:
    if xml.get("{%s}id" % xml_ns) is not None:
        rdg_id = xml.get("{%s}id" % xml_ns)
        rdg_id_parts = rdg_id.split("R")
        rdg_id_parts[1] = xml.get("n")
        xml.set("{%s}id" % xml_ns, "R".join(rdg_id_parts))
    # Then change the reading numbers/IDs specified in the target attribute:
    targets = xml.get("target").split()
    for i, target in enumerate(targets):
        # If the target is a reference to an XML ID, then replace only the last part corresponding to the reading number:
        if target[0] == '#':
            target_parts = target.strip("#").split("R")
            target_parts[1] = transposition_dict[target_parts[1]]
            targets[i] = "#" + "R".join(target_parts)
        # Otherwise, just replace it with the new number:
        else:
            targets[i] = transposition_dict[target]
    targets = sorted(targets, key=reading_reference_key) # ensure that the reading references in the target attribute are sorted appropriately
    xml.set("target", " ".join(targets))
    # Then relabel any certainty elements under this witDetail element:
    for certainty in xml.xpath("./tei:certainty", namespaces={"tei": tei_ns}):
        process_certainty(certainty, transposition_dict)
    # Then, if this witDetail element has certainty elements under it, then sort them:
    if len(xml.xpath("./tei:certainty", namespaces={"tei": tei_ns})) > 0:
        xml[:] = sorted([certainty for certainty in xml], key=certainty_key)
    return

"""
Relabel a relation element, given a dictionary mapping old indices to new indices.
"""
def process_relation(xml, transposition_dict):
    active_targets = xml.get("active").split()
    for i, target in enumerate(active_targets):
        # If the target is a reference to an XML ID, then replace only the last part corresponding to the reading number:
        if target[0] == '#':
            target_parts = target.strip("#").split("R")
            target_parts[1] = transposition_dict[target_parts[1]]
            active_targets[i] = "R".join(target_parts)
        # Otherwise, just replace it with the new number:
        else:
            active_targets[i] = transposition_dict[target]
    active_targets = sorted(active_targets, key=reading_reference_key) # ensure that the reading references in the target attribute are sorted appropriately
    xml.set("active", " ".join(active_targets))
    passive_targets = xml.get("passive").split()
    for i, target in enumerate(passive_targets):
        # If the target is a reference to an XML ID, then replace only the last part corresponding to the reading number:
        if target[0] == '#':
            target_parts = target.strip("#").split("R")
            target_parts[1] = transposition_dict[target_parts[1]]
            passive_targets[i] = "R".join(target_parts)
        # Otherwise, just replace it with the new number:
        else:
            passive_targets[i] = transposition_dict[target]
        passive_targets = sorted(passive_targets, key=reading_reference_key) # ensure that the reading references in the target attribute are sorted appropriately
    xml.set("passive", " ".join(passive_targets))
    return

"""
Relabel a listRelation element, given a dictionary mapping old indices to new indices.
"""
def process_list_relation(xml, transposition_dict):
    # Recursively process each relation under this relationList:
    for relation in xml.xpath("./tei:relation", namespaces={"tei": tei_ns}):
        process_relation(relation, transposition_dict)
    # Then, sort the relations under this listRelation:
    xml[:] = sorted([child for child in xml], key=relation_key)
    return

"""
Relabel the relation elements under a given note element, given a dictionary mapping old reading indices to new indices.
The relation elements are then sorted.
"""
def process_note(xml, transposition_dict):
    # Recursively process each relationList under this note:
    for list_relation in xml.xpath("./tei:listRelation", namespaces={"tei": tei_ns}):
        process_list_relation(list_relation, transposition_dict)
    return

"""
Recursively relabel and reorder the children of an app element, given a dictionary mapping old indices to new indices.
"""
def process_app(xml, transposition_dict):
    # Proceed through the children of this app element:
    for child in xml:
        # If the child is a comment, then skip it:
        if isinstance(child, et._Comment):
            continue
        # Otherwise, process it according to its tag and type:
        raw_tag = child.tag.replace("{%s}" % tei_ns, "")
        if raw_tag == "lem":
            process_lem(child, transposition_dict)
        elif raw_tag == "rdg":
            process_rdg(child, transposition_dict)
        elif raw_tag == "witDetail":
            if child.get("type") is not None and child.get("type") == "ambiguous":
                process_wit_detail(child, transposition_dict)
        elif raw_tag == "note":
            process_note(child, transposition_dict)
    # Then sort the child elements of this app element:
    xml[:] = sorted([child for child in xml], key=rdg_key)
    return

"""
Entry point to the script. Parses command-line arguments and calls the core functions.
"""
def main():
    parser = argparse.ArgumentParser(description="Relabel and reorder the reading elements in the specified variation unit of the given collation file.")
    parser.add_argument("-o", metavar="output", type=str, help="Filename for the reformatted TEI XML output (if none is specified, then the output is written to the console).")
    parser.add_argument("input", type=str, help="TEI XML collation file to modify.")
    parser.add_argument("vu_id", type=str, help="ID of the target variation unit.")
    parser.add_argument("sequence", type=str, help="A parenthesized sequence of comma-separated reading numbers in their desired order; e.g., (4,1,2,3).")
    args = parser.parse_args()
    # Parse the optional arguments:
    output_addr = args.o
    # Parse the positional arguments:
    input_addr = args.input
    vu_id = args.vu_id
    sequence = args.sequence.strip("(").strip(")").split(",")
    # Parse the input XML document:
    xml = et.parse(input_addr)
    # Get the specified variation unit:
    app = xml.xpath(".//tei:app[@xml:id=\"%s\"]" % vu_id, namespaces={"tei": tei_ns})[0]
    # Ensure that the specified sequence contains the same set of substantive readings in the specified variation unit:
    sequence_set = set(sequence)
    substantive_reading_numbers_set = set([rdg.get("n") for rdg in app.xpath("./tei:rdg", namespaces={"tei": tei_ns}) if rdg.get("type") is None])
    if sequence_set != substantive_reading_numbers_set:
        print("ERROR: The specified reading sequence %s does not match the sequence of substantive readings %s in variation unit %s" % (str(sequence_set), str(substantive_reading_numbers_set), vu_id))
        exit(1)
    # If it matches, then produce a dictionary mapping each reading number in the specified sequence to its one-based index in the sequence:
    transposition_dict = {}
    for i, n in enumerate(sequence):
        transposition_dict[n] = str(i + 1)
    # Convert it in place:
    process_app(app, transposition_dict)
    #Then write the XML of this variation unit to output:
    if output_addr is None:
        print(et.tostring(app, encoding="utf-8", xml_declaration=True))
    else:
        tree = et.ElementTree(app)
        tree.write(output_addr, encoding="utf-8", xml_declaration=True)
    exit(0)

if __name__=="__main__":
    main()