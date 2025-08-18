#!/usr/bin/env python3

from pathlib import Path
import argparse
import re
import math
from ete3 import Tree
from tqdm import tqdm # for progress bar

"""
Regular expression pattern for metadata in a tree.
"""
metadata_pattern = re.compile(r"(\[[^\[\]]+\])")

"""
Given a .trees file, counts the number of trees in the file.
"""
def get_trees_count(trees_file:Path):
    trees_count = 0
    with open(trees_file, "r") as f:
        for line in f:
            # Switch for reaching the first tree specification:
            if line.strip().startswith("tree"):
                trees_count += 1
    return trees_count

"""
Given a node in a tree, recursively collapses any length-zero branches separating it from its children.
Leaf nodes (which in this case are nodes with non-empty names) are never deleted.
"""
def collapse_null_branches(node):
    # If this node has no children, then nothing needs to be done:
    if node.is_leaf():
        return
    # Otherwise, recursively process its children: 
    for child in node.get_children():
        collapse_null_branches(child)
    # Then identify any named children with length-zero branches above them after this process:
    named_dist_zero_children = [child for child in node.get_children() if child.dist == 0 and child.name != ""]
    # Next, delete any unnamed children with length-zero branches above them:
    for child in node.get_children():
        if child.dist == 0 and child.name == "":
            child.delete(prevent_nondicotomic=False, preserve_branch_length=True)
    # If there are no named children with length-zero branches above them, then we're done:
    if len(named_dist_zero_children) == 0:
        return
    # Alternatively, if the present node is an extant witness, then it must be preserved in the merge, and we're done:
    if node.name != "":
        # In this case, if it is separated from a named child by a length-zero branch, then notify the user
        # (as this should only happen if two extant witnesses are duplicates):
        if len(named_dist_zero_children) > 0:
            print("WARNING: an extant witness is separated from another extant witness by a branch of length 0. The branch between these witnesses will not be collapsed.")
        return
    # Otherwise, there is a named node separated from the current unnamed node by a length-zero branch, and it takes the current node's place in the merge:
    merge_target = named_dist_zero_children[0]
    # If there are multiple named children separated from this node by length-zero branches, then notify the user
    # (as this should only happen if two extant witnesses are duplicates):
    if len(named_dist_zero_children) > 1:
        print("WARNING: multiple extant witnesses are separated from a common ancestor by branches of length 0. By default, the first one encountered will be treated as the extant ancestor.")
    # Then transfer the current node's children to that node and then delete the current node:
    for child in node.get_children():
        if child == merge_target:
            continue
        node.remove_child(child)
        merge_target.add_child(child)
    node.delete(prevent_nondicotomic=False, preserve_branch_length=True)
    return

"""
Given a .trees file and a string indicating a clade, 
returns a dictionary mapping the partitions of those witnesses in the sampled trees to their posterior probabilities.
Optionally, a burn-in proportion can be specified.
"""
def get_children_distribution(trees_file:Path, target_clade:str, burnin:float=0.0):
    posteriors_by_child = {}
    total_trees = get_trees_count(trees_file)
    burnin_trees = math.ceil(burnin*total_trees)
    trees_processed = 0
    tree = None # placeholder for the current tree being processed
    parsing_translate = False
    # Get a sorted list of target witnesses in the clade, and get its serialization:
    target_wits = sorted(target_clade.strip("(").strip(")").split(","))
    sorted_target_clade = "(" + ",".join(target_wits) + ")"
    with tqdm(total=total_trees-burnin_trees) as pbar:
        with open(trees_file, "r") as f:
            indices_by_id = {}
            ids_by_index = {}
            for line in f:
                # Switch upon reaching the Translate block:
                if not parsing_translate and line.strip().startswith("Translate"):
                    parsing_translate = True
                    continue
                # Switch upon reaching the end of the Translate block:
                if parsing_translate and line.strip().startswith(";"):
                    parsing_translate = False
                    continue
                # Switch for processing all other lines in the translate block:
                if parsing_translate:
                    components = line.strip().strip(",").split()
                    wit_index = components[0]
                    wit_id = components[1]
                    indices_by_id[wit_id] = wit_index
                    ids_by_index[wit_index] = wit_id
                    continue
                # Switch for reaching the first tree specification:
                if line.strip().startswith("tree"):
                    # If we are still within the burn-in bound, then do nothing except increment the processed trees count:
                    if trees_processed < burnin_trees:
                        trees_processed += 1
                        continue
                    # Get the string containing the Newick representation of the tree:
                    newick = line.strip().split(" = ")[1]
                    # Remove all metadata sequences in the tree:
                    newick = re.sub(metadata_pattern, "", newick)
                    # Replace all (metadata, branch length) sequences in the tree to match NHX format:
                    # metadata_branch_length_replacement_map = {}
                    # for match in metadata_branch_length_pattern.findall(newick):
                    #     metadata = match[0]
                    #     branch_length = match[1]
                    #     original = metadata + ":" + branch_length
                    #     replacement = ":" + branch_length + metadata.replace("&", "&&NHX:").replace(",", ":")
                    #     metadata_branch_length_replacement_map[original] = replacement
                    # for original in metadata_branch_length_replacement_map:
                    #     newick = newick.replace(original, metadata_branch_length_replacement_map[original])
                    # Then initialize the tree from this reformatted tree:
                    tree = Tree(newick)
                    # Then, recursively collapse the length-zero branches in the stemma:
                    root = tree.get_tree_root()
                    collapse_null_branches(root)
                    # Now get the node indices for the witnesses in the target clade:
                    target_wit_indices = [indices_by_id[target_wit] for target_wit in target_wits]
                    # Then retrieve the node corresponding to their closest common ancestor:
                    common_ancestor = tree.get_common_ancestor(target_wit_indices) if len(target_wit_indices) > 1 else tree.search_nodes(name=target_wit_indices[0])[0]
                    # If this ancestor has more descendants than the specified witnesses, then the specified clade does not exist in this tree;
                    # mark it accordingly:
                    common_ancestor_witnesses = [node for node in common_ancestor.traverse() if node.name != ""]
                    if len(common_ancestor_witnesses) != len(target_wit_indices):
                        serialized_children = "Clade not present"
                        if serialized_children not in posteriors_by_child:
                            posteriors_by_child[serialized_children] = 0
                        posteriors_by_child[serialized_children] += 1
                        trees_processed += 1
                        pbar.update(1)
                        continue
                    # Then proceed through the children of the common ancestor:
                    children = []
                    for child in common_ancestor.children:
                        # Serialize this child in terms of the IDs of the leaves under it:
                        child_str = "(" + ",".join(sorted([ids_by_index[node.name] for node in child.traverse() if node.name != ""])) + ")"
                        children.append(child_str)
                    serialized_children = str(sorted(children))
                    # If the common ancestor itself is one of the target witnesses, then give this clade a special name:
                    if common_ancestor.name in target_wit_indices:
                        serialized_children = "Extant ancestor " + ids_by_index[common_ancestor.name] + ", children " + serialized_children
                    if serialized_children not in posteriors_by_child:
                        posteriors_by_child[serialized_children] = 0
                    posteriors_by_child[serialized_children] += 1
                    trees_processed += 1
                    pbar.update(1)
    # Finally, normalize the frequencies of the children:
    for child in posteriors_by_child:
        posteriors_by_child[child] = posteriors_by_child[child] / (trees_processed - burnin_trees)
    return posteriors_by_child

"""
Entry point to the script. Parses command-line arguments and calls the core functions.
"""
def main():
    parser = argparse.ArgumentParser(description="Extract a dictionary of posterior probabilities for the splits of a given clade in the sampled trees from a given .trees file.")
    parser.add_argument("trees_input", type=str, help="Input .trees file.")
    parser.add_argument("clade", type=str, help="A string representing the common ancestor of multiple witnesses (e.g., \"(1739,1881)\").")
    parser.add_argument("--burnin", "-b", type=float, default=0.0, help="Burn-in proportion for sampled trees.")
    # Parse the command-line arguments:
    args = parser.parse_args()
    trees_input = args.trees_input
    clade = args.clade
    burnin = args.burnin
    # Do not allow burn-in proportions outside of [0, 1):
    if burnin < 0.0 or burnin >= 1.0:
        print("ERROR: burn-in proportion must be at least 0.0 and less than 1.0.")
        exit(1)
    # Then process the file:
    posteriors_by_child = get_children_distribution(trees_input, clade, burnin)
    for k, v in sorted(posteriors_by_child.items(), key=lambda item: item[1], reverse=True):
        if v > 0.001:
            print("%s: %f\n" % (k, v))
    exit(0)

if __name__=="__main__":
    main()