import typer
from pathlib import Path
from collections import OrderedDict
from lxml import etree as et
from ete3 import Tree
import re
import yaml

"""
XML namespaces
"""
xml_ns = "http://www.w3.org/XML/1998/namespace"
tei_ns = "http://www.tei-c.org/ns/1.0"

def get_state(string):
    m = re.search(r'"(\d*)"', string)
    if not m:
        print("Failed to read", string)
        raise Exception

    return int(m.group(1))    


def tree_from_split(text):        
    start = text.find("=")
    newick = text[start+1:] + ";"
    return Tree(newick, format=1)     


def main(ancestral_trees_file: Path, beast_input_file: Path, out: Path, burnin:float=0.0, limit:int=None):
    # Initialize lists of site labels and lists of lists of state labels:
    site_labels = []
    state_labels = []
    # Parse the BEAST input XML document:
    parser = et.XMLParser(remove_blank_text=True)
    xml = et.parse(beast_input_file, parser=parser)
    for charstatelabels in xml.xpath("//charstatelabels"):
        # Get the site ID and add it to the list of site labels:
        character_name = charstatelabels.get("characterName")
        site_labels.append(character_name)
        # Get its reading values and add a list of them to the list of state labels:
        state_values = charstatelabels.get("value").split(", ")
        state_labels.append(state_values)
    num_trees = 0
    for run in xml.xpath("//run"):
        num_trees = int(run.get("chainLength"))
    for ancestral_state_logger in xml.xpath("//logger[@id=\"ancestralStateLogger\"]"):
        num_trees = num_trees/int(ancestral_state_logger.get("logEvery"))
    burnin_count = int(burnin*num_trees)
    # Initialize the list of lists to be populated:
    root_count = [] # a list of lists, with each inner list corresponding to counts for different states
    for i in range(len(site_labels)):
        root_count.append([0] * len(state_labels[i]))
    taxon_labels = [] # taxon labels
    reading_ancestral_state_file = False # flag indicating if we're parsing the output of an AncestralStateLogger rather than an AncestralSequenceLogger
    reading_labels = False # flag indicating if we're parsing taxon labels
    sample_index = -1
    with open(ancestral_trees_file) as f:
        for line in f:
            line = line.strip()
            # Skip any empty lines:
            if line == "":
                continue
            if line.startswith("site"):
                # If the line starts with "site", then it's the first line of an AncestralStateLogger output:
                reading_ancestral_state_file = True
                continue
            elif line == "Taxlabels" and len(taxon_labels) == 0:
                reading_labels = True
                continue
            elif line ==";":
                reading_labels = False
                continue
            
            if not reading_ancestral_state_file and reading_labels:
                taxon_labels.append(line)
                continue

            # If we're reading an AncestralSequenceLogger output and a new tree occurs on this line, then parse it:
            if not reading_ancestral_state_file and line.startswith("tree "):
                sample_index += 1

                # Skip all indices under the burn-in threshold:
                if sample_index < burnin_count:
                    continue

                # Exit the loop if we've processed the specified limit of trees (if a limit is specified):
                if limit is not None and sample_index - burnin_count + 1 > limit:
                    break

                character_tree_strings = line.split(";")

                for index, location_newick in enumerate(character_tree_strings):
                    if not location_newick.strip():
                        continue

                    # root_count[index]
                    tree = tree_from_split(location_newick)
                    # print(tree)
                    # print(dir(tree))
                    # print(tree.is_root())
                    # print(tree.show())
                    # print(get_state(tree.name))
                    try:
                        state = get_state(tree.name)
                    except Exception:
                        continue

                    root_count[index][state] += 1
            # If we're reading an AncestralStateLogger output, then parse the entries on this line:
            elif reading_ancestral_state_file:
                sample_index += 1
                # Skip all indices under the burn-in threshold:
                if sample_index < burnin_count:
                    continue
                # Exit the loop if we've processed the specified limit of trees (if a limit is specified):
                if limit is not None and sample_index - burnin_count + 1 > limit:
                    break
                character_state_strings = line.split("\t")
                for index, state_str in enumerate(character_state_strings):
                    state = int(state_str)
                    root_count[index][state] += 1
        # print(root_count)
        # Finally, convert the list of lists containing state counts to a dictionary of dictionaries:
        root_probabilities_by_site = {}
        for i in range(len(root_count)):
            site_label = site_labels[i]
            root_probabilities_by_site[site_label] = {}
            total_count_for_site = sum(root_count[i])
            for j in range(len(root_count[i])):
                state_label = state_labels[i][j]
                root_probabilities_by_site[site_label][state_label] = root_count[i][j] / total_count_for_site
            # If the total count of labels for this site do not equal the number of ancestral trees/states sampled,
            # then report this variation unit:
            if total_count_for_site != sample_index - burnin_count + 1:
                print("WARNING: in site %d (ID %s), only %d samples were counted, but %d root states were sampled." % (i, site_label, total_count_for_site, sample_index - burnin_count + 1))
            # If the set of distinct reading labels is shorter than the list of reading labels, 
            # then report this variation unit:
            if len(set(state_labels[i])) != len(state_labels[i]):
                print("WARNING: in site %d (ID %s), there are duplicate state labels in %s." % (i, site_label, str(state_labels[i])))
        with open(out, "w", encoding="utf-8") as outfile:
            yaml.dump(root_probabilities_by_site, outfile, sort_keys=False, allow_unicode=True)

        return 

if __name__ == "__main__":
    typer.run(main)
