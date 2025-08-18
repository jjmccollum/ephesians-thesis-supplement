#!/usr/bin/env python3

import argparse
import math
from lxml import etree as et # for reading TEI XML inputs
import teiphy as tp # for converting a TEI XML collation to a dataset of reading support vectors
import pandas as pd # for writing to tabular outputs

def format_reading_text(text):
    """
    Given the serialized text of a reading, format it for printing.
    """
    out_text = text
    # If the text is empty, it is an omission:
    if out_text == "":
        out_text = "\u2013"
        return out_text
    # Otherwise, strip any excess whitespace:
    out_text = out_text.replace("\n", "")
    while "  " in out_text:
        out_text = out_text.replace("  ", " ")
    return out_text

def get_idf_weighted_agreements(xml, target_witnesses, disagree_witnesses=[], manuscript_suffixes=[], trivial_reading_types=[], missing_reading_types=[], fill_corrector_lacunae=False, fragmentary_threshold=None, split_missing = None):
    """
    Given an XML tree representing a TEI collation, a list of target witness sigla, a list of reading types to consider trivial, and other optional arguments to teiphy,
    returns a list of records for readings where the given witnesses agree, sorted by the inverse document frequency (IDF) weight of the support for their readings.
    """
    # First, process the input collation with teiphy:
    coll = tp.Collation(xml, manuscript_suffixes=manuscript_suffixes, trivial_reading_types=trivial_reading_types, missing_reading_types=missing_reading_types, fill_corrector_lacunae=fill_corrector_lacunae, fragmentary_threshold=fragmentary_threshold)
    # Populate a list of sites that will correspond to columns of the sequence alignment:
    variation_unit_ids = set(coll.variation_unit_ids)
    # Initialize the output array with the appropriate dimensions:
    witness_labels = [wit.id for wit in coll.witnesses]
    witness_labels_set = set(witness_labels)
    # As a sanity check, make sure no specified witnesses were excluded because they are below the fragmentary witness threshold:
    if fragmentary_threshold is not None:
        fragmentary_specified_witnesses = [wit for wit in target_witnesses if wit not in witness_labels_set] + [wit for wit in disagree_witnesses if wit not in witness_labels_set]
        if len(fragmentary_specified_witnesses) > 0:
            print("ERROR: the specified witnesses %s are not present in the filtered witness list. They may be too lacunose to pass the fragmentary witness threshold of %f." % (str(fragmentary_specified_witnesses), fragmentary_threshold))
            exit(1)
    # For each variation unit, keep a record of the proportion of non-missing witnesses supporting the substantive variant readings:
    support_proportions_by_unit = {}
    for j, vu_id in enumerate(coll.variation_unit_ids):
        support_proportions = [0.0] * len(coll.substantive_readings_by_variation_unit_id[vu_id])
        for i, wit in enumerate(coll.witnesses):
            rdg_support = coll.readings_by_witness[wit.id][j]
            for l, w in enumerate(rdg_support):
                support_proportions[l] += w
        norm = sum(support_proportions)
        for l in range(len(support_proportions)):
            support_proportions[l] = support_proportions[l] / norm
        support_proportions_by_unit[vu_id] = support_proportions
    # Then populate the list of agreements one variation unit at a time:
    total_variation_units = len(variation_unit_ids)
    event_variation_units = 0
    total_expected_information_content = 0.0
    idf_weighted_agreements = []
    for k, vu in enumerate(coll.variation_units):
        vu_id = vu.id
        if vu_id not in variation_unit_ids:
            continue
        substantive_reading_ids = coll.substantive_readings_by_variation_unit_id[vu_id]
        substantive_reading_ids_set = set(substantive_reading_ids)
        substantive_reading_texts = [format_reading_text(rdg.text) for rdg in vu.readings if rdg.id in substantive_reading_ids_set]
        # Calculate the sampling probabilities for each reading in this unit:
        sampling_probabilities = [0.0] * len(substantive_reading_ids)
        rdg_support_by_witness = {}
        for i, wit in enumerate(witness_labels):
            rdg_support = coll.readings_by_witness[wit][k]
            # Check if this reading support vector represents missing data:
            norm = sum(rdg_support)
            if norm == 0:
                # If this reading support vector sums to 0, then this is missing data; handle it as specified:
                if split_missing == "uniform":
                    rdg_support = [1 / len(rdg_support) for l in range(len(rdg_support))]
                elif split_missing == "proportional":
                    rdg_support = [support_proportions_by_unit[vu_id][l] for l in range(len(rdg_support))]
            else:
                # Otherwise, the data is present, though it may be ambiguous; normalize the reading probabilities to sum to 1:
                rdg_support = [w / norm for l, w in enumerate(rdg_support)]
            # Save this vector of probabilities for this witness:
            rdg_support_by_witness[wit] = rdg_support
            # Then add this witness's contributions to the readings' sampling probabilities:
            for l, w in enumerate(rdg_support):
                sampling_probabilities[l] += w
        # Then normalize the sampling probabilities so they sum to 1:
        norm = sum(sampling_probabilities)
        sampling_probabilities = [w / norm for w in sampling_probabilities]
        # Next, calculate the base probabilities for the specified agreements and disagreements for each reading:
        event_probabilities_by_reading = [1.0] * len(substantive_reading_ids)
        for wit in target_witnesses:
            rdg_support = rdg_support_by_witness[wit]
            for l, w in enumerate(rdg_support):
                event_probabilities_by_reading[l] *= w
        for wit in disagree_witnesses:
            rdg_support = rdg_support_by_witness[wit]
            for l, w in enumerate(rdg_support):
                event_probabilities_by_reading[l] *= (1 - w)
        event_probability = sum(event_probabilities_by_reading)
        # If the target witnesses do not agree and disagree as specified at this variation unit, then we can skip this unit:
        if event_probability == 0:
            continue
        # Otherwise, increment the counter for variation units at which the specified agreements and disagreements occur:
        event_variation_units += 1
        # Then populate a list of witnesses that support (or potentially support) each reading:
        supporting_wits_by_reading = []
        for l in range(len(substantive_reading_ids)):
            supporting_wits_by_reading.append([])
        for wit in witness_labels:
            rdg_support = rdg_support_by_witness[wit]
            for l, w in enumerate(rdg_support):
                if w == 1.0:
                    supporting_wits_by_reading[l].append(wit)
                elif w > 0:
                    supporting_wits_by_reading[l].append(wit + "?")
        # Then populate a record for each possible event with a non-zero information content, along with information about it:
        for l in range(len(substantive_reading_ids)):
            if event_probabilities_by_reading[l] == 0.0:
                continue
            if sampling_probabilities[l] == 0.0:
                continue
            rdg_id = substantive_reading_ids[l]
            rdg_text = substantive_reading_texts[l]
            expected_information_content = -math.log2(sampling_probabilities[l]) * event_probabilities_by_reading[l] / event_probability # the expected information content (in bits) for this reading given the specified agreements and disagreements on this reading:
            if expected_information_content == 0:
                continue
            total_expected_information_content += expected_information_content
            agreement = {}
            agreement["app"] = vu_id
            agreement["rdg_id"] = substantive_reading_ids[l]
            agreement["rdg_text"] = substantive_reading_texts[l]
            agreement["witnesses"] = " ".join(supporting_wits_by_reading[l])
            agreement["expected_information_content (bits)"] = expected_information_content
            idf_weighted_agreements.append(agreement)
    print("Total variation units: %d" % total_variation_units)
    print("Variation units with specified agreements and disagreements: %d" % event_variation_units)
    print("Total expected information content, assuming specified agreements and disagreements: %f" % total_expected_information_content)
    return sorted(idf_weighted_agreements, key=lambda agreement: agreement["expected_information_content (bits)"], reverse=True)
            
"""
Entry point to the script. Parses command-line arguments and calls the core functions.
"""
def main():
    parser = argparse.ArgumentParser(usage="get_idf_agreements.py [-h] [-s suffix -s suffix ...] [-t type -t type ...] [-m type -m type ...] [--fill-correctors] [-f threshold] [-d witness -d witness ...] [-l threshold] [-o output] collation witness [witness ...]", description="Returns a list of readings shared by the given witnesses (or attested by a single given witness), sorted by the inverse document frequency (IDF) weights of those readings' attestations.")
    parser.add_argument("-s", "--suffix", metavar="type", type=str, default=[], action="append", help="Witness suffixes to ignore (e.g., \"*\", \"T\", \"/1\", \"-1\"). This option can be repeated multiple times.")
    parser.add_argument("-t", "--trivial", metavar="type", type=str, default=[], action="append", help="Reading types to treat as trivial (e.g., \"reconstructed\", \"defective\", \"orthographic\", \"subreading\"). This option can be repeated multiple times.")
    parser.add_argument("-m", "--missing", metavar="type", type=str, default=[], action="append", help="Reading types to treat as missing (e.g., \"lac\", \"overlap\"). This option can be repeated multiple times.")
    parser.add_argument("--fill-correctors", action="store_true", help="Fill in missing readings in witnesses with type \"corrector\" using the witnesses they follow in the TEI XML witness list.")
    parser.add_argument("-f", "--fragmentary-threshold", metavar="fragmentary_threshold", type=float, default=0.0, help="Ignore all witnesses that are extant at fewer than the specified proportion of variation units. For the purposes of this calculation, a witness is considered non-extant/lacunose at a variation unit if the type of its reading in that unit is in the user-specified list of missing reading types (i.e., the argument(s) of the -m option). This calculation is performed after the reading sequences of correctors have been filled in (if the --fill-correctors flag was specified). Thus, a threshold of 0.7 means that a witness with missing readings at more than 30 percent of variation units will be excluded from the output.")
    parser.add_argument("--split-missing", metavar="split_missing", type=str, choices=["uniform", "proportional"], help="Treat missing characters/variation units as having a contribution of 1 split over all states/readings.\nIf not specified, then missing data is ignored (i.e., all states are 0).\nIf \"uniform\", then the contribution of 1 is divided evenly over all substantive readings.\nIf \"proportional\", then the contribution of 1 is divided between the readings in proportion to their support among the witnesses that are not missing.")
    parser.add_argument("-d", "--disagree", metavar="witness", type=str, default=[], action="append", help="One or more witnesses with which the agreeing witnesses must disagree. This option can be repeated multiple times.")
    parser.add_argument("-l", "--low", metavar="low", type=float, default=0.0, help="Lowest IDF score to include in the output.")
    parser.add_argument("-o", "--output", metavar="output", type=str, help="Address of output file. Supported formats are .xlsx, .csv, and .tsv. If none is specified, then the output will be written to the command line.")
    parser.add_argument("collation", type=str, help="Address of collation file.")
    parser.add_argument("witness", metavar="witness", type=str, help="Witness whose readings are to be considered.")
    parser.add_argument("extra_witnesses", metavar="witness", nargs="*", type=str, default=[], help=argparse.SUPPRESS)
    args = parser.parse_args()
    # Parse the positional arguments:
    collation_addr = args.collation
    target_witnesses = [args.witness] + args.extra_witnesses
    # Parse the optional arguments:
    suffixes = args.suffix
    trivial_reading_types = args.trivial
    missing_reading_types = args.missing
    fill_corrector_lacunae = args.fill_correctors
    fragmentary_threshold = args.fragmentary_threshold
    split_missing = args.split_missing
    disagree_witnesses = args.disagree
    low = args.low
    output_addr = args.output
    # Ensure that none of the target witnesses are in the disagree set:
    target_witnesses_set = set(target_witnesses)
    disagree_witnesses_set = set(disagree_witnesses)
    witnesses_intersection = target_witnesses_set.intersection(disagree_witnesses_set)
    if len(witnesses_intersection) > 0:
        print("ERROR: the witnesses %s are in both the target set and the disagree set. They cannot be specified in both!")
        exit(1)
    if fragmentary_threshold is not None and (fragmentary_threshold < 0.0 or fragmentary_threshold > 1.0):
        print("ERROR: the fragmentary variation unit proportion threshold is %f. It must be a value in [0, 1]." % fragmentary_threshold)
        exit(1)
    # Parse the input XML document:
    parser = et.XMLParser(remove_comments=True)
    xml = et.parse(collation_addr, parser=parser)
    # Then populate the output list:
    idf_weighted_agreements = get_idf_weighted_agreements(xml, target_witnesses, disagree_witnesses, suffixes, trivial_reading_types, missing_reading_types, fill_corrector_lacunae, fragmentary_threshold, split_missing)
    # Then print the output:
    df = pd.DataFrame(idf_weighted_agreements)
    df = df[df["expected_information_content (bits)"] >= low]
    # If no output file was specified, then write to the command line:
    if output_addr is None:
        print(df.to_string())
        exit(0)
    # Otherwise, write to an output according to its file extension:
    if output_addr.endswith(".xlsx"):
        df.to_excel(output_addr)
        exit(0)
    if output_addr.endswith(".csv"):
        df.to_csv(output_addr, encoding="utf-8-sig")  # add BOM to start of file so that Excel will know to read it as Unicode
        exit(0)
    if output_addr.endswith(".tsv"):
        df.to_csv(output_addr, encoding="utf-8-sig", sep="/t")  # add BOM to start of file so that Excel will know to read it as Unicode
        exit(0)
    # If the file has none of these extensions, then warn the user:
    print("ERROR: an output with an unexpected file type was specified. Please specify a file with an extension in {.xlsx, .csv, .tsv}.")
    exit(1)

if __name__=="__main__":
    main()