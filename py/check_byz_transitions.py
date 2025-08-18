import argparse
from lxml import etree as et  # for reading TEI XML inputs

"""
XML namespaces
"""
xml_ns = "http://www.w3.org/XML/1998/namespace"
tei_ns = "http://www.tei-c.org/ns/1.0"

def check_byz_transitions(xml):
    """
    Checks all variation units in the given TEI XML collation
    and reports if there is a mismatch between the readings supported by RP or RPmarg
    and the readings targeted by the "Byz" transcriptional change class.
    """
    # Proceed for every variation unit:
    for app in xml.xpath("//tei:app", namespaces={"tei": tei_ns}):
        app_id = app.get("{%s}id" % xml_ns)
        # First, determine which readings are Byzantine:
        byz_readings = set()
        current_substantive_rdg = ""
        for rdg in app.xpath(".//tei:rdg", namespaces={"tei": tei_ns}):
            rdg_id = rdg.get("{%s}id" % xml_ns) if rdg.get("{%s}id" % xml_ns) is not None else rdg.get("n")
            rdg_type = rdg.get("type")
            if rdg_type is None:
                current_substantive_rdg = rdg_id
            wits = rdg.get("wit").split()
            for wit in wits:
                if wit == "RP" or wit == "RPmarg":
                    byz_readings.add(current_substantive_rdg)
        # If this unit has only one substantive reading, then skip it:
        if current_substantive_rdg == "1" or current_substantive_rdg.endswith("R1"):
            continue
        # Then determine which readings are targets of Byzantinization:
        byz_target_readings = set()
        for relation in app.xpath(".//tei:listRelation[@type=\"transcriptional\"]/tei:relation", namespaces={"tei": tei_ns}):
            if relation.get("ana") != "#Byz":
                continue
            for target_rdg in relation.get("passive").split():
                byz_target_readings.add(target_rdg.strip("#"))
        # If the sets do not match, then report this:
        if len(byz_readings ^ byz_target_readings) > 0:
            print("In variation unit %s, Byzantine readings are %s, but target readings of Byzantinization are %s." % (app_id, str(byz_readings), str(byz_target_readings)))

"""
Entry point to the script. Parses command-line arguments and calls the core functions.
"""
def main():
    parser = argparse.ArgumentParser(description="Checks all variation units in the given TEI XML collation and reports if there is a mismatch between the readings supported by RP or RPmarg and the readings targeted by the \"Byz\" transcriptional change class.")
    parser.add_argument("collation", type=str, help="Address of collation file.")
    args = parser.parse_args()
    # Parse the positional arguments:
    collation_addr = args.collation
    # Parse the input XML document:
    xml = et.parse(collation_addr)
    # Then check the XML:
    check_byz_transitions(xml)

if __name__=="__main__":
    main()