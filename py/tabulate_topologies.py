import typer
from pathlib import Path
import re
from ete3 import Tree
import yaml

branch_rate_pattern = re.compile(r"\[&rate=[^\[\]]+\]")

def tree_from_line(text: str):
    """
    Returns a tree from a single line of the .trees file.
    Any branch rate and branch length data will be stripped from the line.
    """
    start = text.find("=")
    newick = text[start+1:] + ";"
    # Remove all rate information from the tree string, as ETE doesn't process it:
    newick = re.sub(branch_rate_pattern, "", newick)
    return Tree(newick, format=0)

def main(trees_input: Path, topologies_output: Path, tabulations_output: Path):
    # Initialize a list of distinct topologies and a dictionary that will map serialized tree topologies to their number of occurrences in the posterior distribution:
    distinct_topologies = []
    posterior_by_topology = {}
    # First, record and count the topologies from the .trees file:
    with open(trees_input) as f:
        for line in f:
            line = line.strip()
            # If this line contains the information about a sampled tree, then process it:
            if line.startswith("tree "):
                tree = tree_from_line(line)
                topology = tree.write(format=9).strip(";") # the topology only needs to contain the leaf labels
                if topology not in posterior_by_topology:
                    distinct_topologies.append(topology)
                    posterior_by_topology[topology] = 0
                posterior_by_topology[topology] += 1
    # Then normalize the counts in the dictionary to get the posterior probabilities:
    for topology in distinct_topologies:
        posterior_by_topology[topology] = float(posterior_by_topology[topology] / len(distinct_topologies))
    # Then write the distinct topologies to their output file:
    with open(topologies_output, "w") as f:
        for topology in distinct_topologies:
            f.write(topology + ";")
    # Then write the posterior distribution dictionary to a YAML file:
    with open(tabulations_output, "w") as f:
        yaml.dump(posterior_by_topology, f, default_flow_style=False)
    exit(0)

if __name__ == "__main__":
    typer.run(main)