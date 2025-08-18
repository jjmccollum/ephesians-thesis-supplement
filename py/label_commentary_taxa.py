#!/usr/bin/env python3

import argparse

labeled_taxa_by_taxon = {
    "018": "018.Dam",
    "056": "056.C165d",
    "075": "075.C165a",
    "0142": "0142.C165d",
    "0150": "0150.Dam",
    "0151": "0151.Dam",
    "94": "94.C165a",
    "442": "442.C165e",
    "606": "606.Thd",
    "1678": "1678.Zg",
    "1840": "1840.Zg",
    "1908": "1908.C165a",
    "1910": "1910.C162",
    "1913": "1913.Thph",
    "1939": "1939.Thd",
    "1942": "1942.Chr",
    "1962": "1962.Chr",
    "1963": "1963.Thd",
    "1985": "1985.Thph",
    "1987": "1987.Thph",
    "1991": "1991.Thph",
    "1996": "1996.Thd",
    "1999": "1999.Thd",
    "2008": "2008.Zg",
    "2011": "2011.C165a",
    "2012": "2012.Thd",
    "2576": "2576.Thph",
}

"""
Given a .tree or .trees file, 
writes an output .tree or .trees file where the taxon names have Parpulov's commentary labels added.
"""
def label_commentary_taxa(trees_file, output_file):
    with open(output_file, "w", encoding="utf-8") as out:
        with open(trees_file, "r", encoding="utf-8") as f:
            reading_taxlabels = False
            reading_translate = False
            for line in f:
                # Are we currently processing a Taxlabels or Translate block?
                if (not reading_taxlabels and not reading_translate):
                    # If not, then set the appropriate flag if we've entered the corresponding block:
                    if line.strip() == "Taxlabels":
                        reading_taxlabels = True
                    elif line.strip() == "Translate":
                        reading_translate = True
                    # Then copy this line as-is and proceed to the next line:
                    out.write(line)
                elif (reading_taxlabels):
                    # If this is the closing line to the block, then change the processing flag and copy the line as-is:
                    if line.strip() == ";":
                        reading_taxlabels = False
                        reading_translate = False
                        out.write(line)
                        continue
                    # Otherwise, if we're in the Taxlabels block,
                    # then check the current taxon label and replace it as necessary:
                    taxon = line.strip()
                    if taxon in labeled_taxa_by_taxon:
                        labeled_taxon = labeled_taxa_by_taxon[taxon]
                        out.write(line.replace(taxon, labeled_taxon))
                    else:
                        out.write(line)
                else:
                    # If this is the closing line to the block, then change the processing flag and copy the line as-is:
                    if line.strip() == ";":
                        reading_taxlabels = False
                        reading_translate = False
                        out.write(line)
                        continue
                    # Otherwise, we're in the Translate block;
                    # check the current taxon label and replace it as necessary:
                    taxon = line.strip().split(" ")[1].strip(",")
                    if taxon in labeled_taxa_by_taxon:
                        labeled_taxon = labeled_taxa_by_taxon[taxon]
                        out.write(line.replace(taxon, labeled_taxon))
                    else:
                        out.write(line)
    return

"""
Entry point to the script. Parses command-line arguments and calls the core functions.
"""
def main():
    parser = argparse.ArgumentParser(description="Given an input .tree or .trees file, writes an output .tree or .trees file where the taxon names have Parpulov's commentary labels added.")
    parser.add_argument("trees_file", type=str, help="The input .tree or .trees file.")
    parser.add_argument("output_file", type=str, help="The output .tree or .trees with commentary labels added to taxa.")
    args = parser.parse_args()
    # Parse the positional arguments:
    trees_file = args.trees_file
    output_file = args.output_file
    label_commentary_taxa(trees_file, output_file)
    exit(0)

if __name__=="__main__":
    main()