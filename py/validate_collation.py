#!/usr/bin/env python3

import argparse
from lxml import etree as et

"""
XML namespaces
"""
xml_ns = 'http://www.w3.org/XML/1998/namespace'
tei_ns = 'http://www.tei-c.org/ns/1.0'

"""
Given a witness siglum and lists of suffixes,
returns the base siglum of the witness, stripped of all suffixes, and a list of its suffixes in the order they occur
"""
def parse_wit(wit, first_hand_suffixes, main_text_suffixes, corrector_suffixes, alternate_suffixes, multiple_suffixes):
    base_wit = wit
    suffixes = []
    while (True):
        suffix = ''
        for first_hand_suffix in first_hand_suffixes:
            if base_wit.endswith(first_hand_suffix):
                suffix = first_hand_suffix
                break
        for main_text_suffix in main_text_suffixes:
            if base_wit.endswith(main_text_suffix):
                suffix = main_text_suffix
                break
        for corrector_suffix in corrector_suffixes:
            if base_wit.endswith(corrector_suffix):
                suffix = corrector_suffix
                break
        for alternate_suffix in alternate_suffixes:
            if base_wit.endswith(alternate_suffix):
                suffix = alternate_suffix
                break
        for multiple_suffix in multiple_suffixes:
            if base_wit.endswith(multiple_suffix):
                suffix = multiple_suffix
                break
        if len(suffix) == 0:
            break
        base_wit = base_wit[:-len(suffix)]
        suffixes = [suffix] + suffixes
    return base_wit, suffixes

"""
Given the XML tree for an element, recursively serializes it in a more readable format.
"""
def serialize(xml):
    #Get the element tag:
    raw_tag = xml.tag.replace('{%s}' % tei_ns, '')
    #If it is a reading, then serialize its children, separated by spaces:
    if raw_tag == 'rdg':
        text = '' if xml.text is None else xml.text
        text += ' '.join([serialize(child) for child in xml])
        return text
    #If it is a word, abbreviation, or overline-rendered element, then serialize its text and tail, 
    #recursively processing any subelements:
    if raw_tag in ['w', 'abbr', 'hi']:
        text = '' if xml.text is None else xml.text
        text += ''.join([serialize(child) for child in xml])
        text += '' if xml.tail is None else xml.tail
        return text
    #If it is a space, then serialize as a single space:
    if raw_tag == 'space':
        text = '['
        text += 'space'
        if xml.get('reason') is not None:
            text += ' '
            reason = xml.get('reason')
            text += '(' + reason + ')'
        if xml.get('unit') is not None and xml.get('extent') is not None:
            text += ', '
            unit = xml.get('unit')
            extent = xml.get('extent')
            text += extent + ' ' + unit
        text += ']'
        text += '' if xml.tail is None else xml.tail
        return text
    #If it is an expansion, then serialize it in parentheses:
    if raw_tag == 'ex':
        text = ''
        text += '('
        text += '' if xml.text is None else xml.text
        text += ' '.join([serialize(child) for child in xml])
        text += ')'
        text += '' if xml.tail is None else xml.tail
        return text
    # If it is a gap, then serialize it based on its attributes:
    if raw_tag == 'gap':
        text = ''
        text += '['
        text += 'gap'
        if xml.get('reason') is not None:
            text += ' '
            reason = xml.get('reason')
            text += '(' + reason + ')'
        if xml.get('unit') is not None and xml.get('extent') is not None:
            text += ', '
            unit = xml.get('unit')
            extent = xml.get('extent')
            text += extent + ' ' + unit
        else:
            text += '...'
        text += ']'
        text += '' if xml.tail is None else xml.tail
        return text
    #If it is an unclear or supplied element, then recursively set the contents in brackets:
    if raw_tag in ['unclear', 'supplied']:
        text = ''
        text += '['
        text += '' if xml.text is None else xml.text
        text += ' '.join([serialize(child) for child in xml])
        text += ']'
        text += '' if xml.tail is None else xml.tail
        return text
    #If it is a choice element, then recursively set the contents in brackets, separated by slashes:
    if raw_tag == 'choice':
        text = ''
        text += '['
        text += '' if xml.text is None else xml.text
        text += '/'.join([serialize(child) for child in xml])
        text += ']'
        text += '' if xml.tail is None else xml.tail
        return text
    #If it is a ref element, then set its text in brackets:
    if raw_tag == 'ref':
        text = ''
        text += '['
        text += '' if xml.text is None else xml.text
        text += ']'
        text += '' if xml.tail is None else xml.tail
        return text
    #For all other elements, return an empty string:
    return ''

"""
Given an XML tree, identifies and reports all instances of duplicate readings (based on their texts)
in a passage.
"""
def find_duplicate_readings(xml):
    for app in xml.xpath('//tei:app', namespaces={'tei': tei_ns}):
        rdgs_by_text = {}
        for rdg in app.xpath('tei:rdg', namespaces={'tei': tei_ns}):
            #Ignore overlaps and lacunae for this purpose:
            if rdg.get('type') is not None and rdg.get('type') in ['overlap', 'lac']:
                continue
            rdg_text = serialize(rdg)
            if rdg_text not in rdgs_by_text:
                rdgs_by_text[rdg_text] = []
            rdgs_by_text[rdg_text].append(rdg.get('n'))
        for rdg_text in rdgs_by_text:
            if len(rdgs_by_text[rdg_text]) > 1:
                print('Reading %s occurs in readings %s in variation unit %s.' % (rdg_text, str(rdgs_by_text[rdg_text]), app.get('{%s}id' % xml_ns)))
    return

"""
Given an XML tree, identifies and reports all instances of a witness supporting more than one reading 
in a passage.
"""
def find_ambiguous_attestations(xml):
    for app in xml.xpath('//tei:app', namespaces={'tei': tei_ns}):
        rdgs_by_wit = {}
        for rdg in app.xpath('tei:rdg', namespaces={'tei': tei_ns}):
            for wit in rdg.get('wit').split():
                if wit not in rdgs_by_wit:
                    rdgs_by_wit[wit] = []
                rdgs_by_wit[wit].append(rdg.get('n'))
        for wit in rdgs_by_wit:
            if len(rdgs_by_wit[wit]) > 1:
                print('Witness %s supports readings %s in variation unit %s.' % (wit, str(rdgs_by_wit[wit]), app.get('{%s}id' % xml_ns)))
    return

"""
Given an XML and sets of first hand, main text, corrector, and alternate reading suffixes,
identifies and reports instances of unmatched (first hand, corrector) and (main text, alternate) pairs
in a passage.
"""
def find_unmatched_witness_pairs(xml, first_hand_suffixes, main_text_suffixes, corrector_suffixes, alternate_suffixes, multiple_suffixes):
    for app in xml.xpath('//tei:app', namespaces={'tei': tei_ns}):
        # First, populate a map from witness sigla (with suffixes included) to the numbers of their supported readings
        # and another map from base witnesses to a list of their subwitness suffix lists
        rdgs_by_wit = {}
        suffixes_by_base_wit = {}
        for rdg in app.xpath('tei:rdg', namespaces={'tei': tei_ns}):
            for wit in rdg.get('wit').split():
                if wit not in rdgs_by_wit:
                    rdgs_by_wit[wit] = []
                rdgs_by_wit[wit].append(rdg.get('n'))
                # Get the base witness siglum and a list of any attached suffixes in the order they appear:
                base_wit, suffixes = parse_wit(wit, first_hand_suffixes, main_text_suffixes, corrector_suffixes, alternate_suffixes, multiple_suffixes)
                if base_wit not in suffixes_by_base_wit:
                    suffixes_by_base_wit[base_wit] = []
                suffixes_by_base_wit[base_wit].append(suffixes)
        # Then proceed through the list of suffix lists for each base witness siglum:
        for base_wit in suffixes_by_base_wit:
            suffix_lists = suffixes_by_base_wit[base_wit]
            # If this base witness has only one suffix list and that suffix list is non-empty, then report this and move on:
            if len(suffix_lists) == 1:
                if len(suffix_lists[0]) != 0:
                    subwit = base_wit + ''.join(suffix_lists[0])
                    print('Subwitness %s (reading %s) occurs without any corresponding subwitness in variation unit %s.' % (subwit, rdgs_by_wit[subwit][0], app.get('{%s}id' % xml_ns)))
                continue
            # Otherwise, ensure that each subwitness is matched for each of its suffixes by at least one other subwitness:
            for suffix_list in suffix_lists:
                # If this suffix list is empty, then the base witness is listed alongside subwitnesses; report this:
                if len(suffix_list) == 0:
                    print('Base witness %s (reading %s) is listed alongside subwitness(es) %s in variation unit %s.' % (base_wit, rdgs_by_wit[base_wit][0], str([base_wit + ''.join(other_suffix_list) for other_suffix_list in suffix_lists if len(suffix_list) > 0]), app.get('{%s}id' % xml_ns)))
                subwit = base_wit + ''.join(suffix_list)
                for i, suffix in enumerate(suffix_list):
                    suffix_matched = False
                    for other_suffix_list in suffix_lists:
                        if i >= len(other_suffix_list):
                            continue
                        other_suffix = other_suffix_list[i]
                        if other_suffix == suffix:
                            continue
                        # If the suffixes correspond, then declare the suffix matched and move on the next suffix:
                        if suffix in first_hand_suffixes and other_suffix in corrector_suffixes:
                            suffix_matched = True
                            break
                        if suffix in corrector_suffixes and other_suffix in first_hand_suffixes:
                            suffix_matched = True
                            break
                        if suffix in main_text_suffixes and other_suffix in alternate_suffixes:
                            suffix_matched = True
                            break
                        if suffix in alternate_suffixes and other_suffix in main_text_suffixes:
                            suffix_matched = True
                            break
                        if suffix in multiple_suffixes and other_suffix in multiple_suffixes:
                            suffix_matched = True
                            break
                    # If the suffix has no match, then report this:
                    if not suffix_matched:
                        if suffix in first_hand_suffixes:
                            print('Found first hand %s with reading %s, but no corrector in variation unit %s.' % (subwit, str(rdgs_by_wit[subwit][0]), app.get('{%s}id' % xml_ns)))
                        if suffix in corrector_suffixes:
                            print('Found corrector %s with reading %s, but no first hand in variation unit %s.' % (subwit, str(rdgs_by_wit[subwit][0]), app.get('{%s}id' % xml_ns)))
                        if suffix in main_text_suffixes:
                            print('Found main text %s with reading %s, but no alternate text in variation unit %s.' % (subwit, str(rdgs_by_wit[subwit][0]), app.get('{%s}id' % xml_ns)))
                        if suffix in alternate_suffixes:
                            print('Found alternate text %s with reading %s, but no main text in variation unit %s.' % (subwit, str(rdgs_by_wit[subwit][0]), app.get('{%s}id' % xml_ns)))
                        if suffix in multiple_suffixes:
                            print('Found multiple attestation %s with reading %s, but no other attestation in variation unit %s.' % (subwit, str(rdgs_by_wit[subwit][0]), app.get('{%s}id' % xml_ns)))
    return
        
"""
Entry point to the script. Parses command-line arguments and calls the core functions.
"""
def main():
    parser = argparse.ArgumentParser(description='Locates all instances in the given TEI XML file where a manuscript supports more than one reading in the same variation unit.')
    parser.add_argument('-f','--firsthand', metavar='siglum', type=str, action='append', help='Suffix for first hand of a witness (e.g., *). If more than one suffix is used, this argument can be specified multiple times.')
    parser.add_argument('-t','--maintext', metavar='siglum', type=str, action='append', help='Suffix for the main text of a witness (e.g., T). If more than one suffix is used, this argument can be specified multiple times.')
    parser.add_argument('-c','--corrector', metavar='siglum', type=str, action='append', help='Suffix for the corrector of a witness (e.g., C, C1, C2), to correspond to the first hand. If more than one suffix is used, this argument can be specified multiple times.')
    parser.add_argument('-a','--alternate', metavar='siglum', type=str, action='append', help='Suffix for an alternate, marginal, or commentary reading of a witness (e.g., A, Z, K), to correspond to the main text. If more than one suffix is used, this argument can be specified multiple times.')
    parser.add_argument('-m','--multiple', metavar='siglum', type=str, action='append', help='Suffix for a witness with multiple attestations at a variation unit (e.g., /1, /2). This argument can be specified multiple times.')
    parser.add_argument('input', type=str, help='TEI XML file to check.')
    args = parser.parse_args()
    #Parse the optional arguments:
    first_hand_suffixes = args.firsthand
    main_text_suffixes = args.maintext
    corrector_suffixes = args.corrector
    alternate_suffixes = args.alternate
    multiple_suffixes = args.multiple
    #Parse the I/O arguments:
    input_addr = args.input
    #Parse the input XML document:
    xml = et.parse(input_addr)
    #Run validation checks:
    find_duplicate_readings(xml)
    find_ambiguous_attestations(xml)
    find_unmatched_witness_pairs(xml, first_hand_suffixes, main_text_suffixes, corrector_suffixes, alternate_suffixes, multiple_suffixes)
    exit(0)

if __name__=="__main__":
    main()