#!/usr/bin/env python3

import argparse

"""
Given a .log file and a .trees file (assumed to be output from the same BEAST 2 run), 
writes an output .tree file whose only tree is the one in the .trees file
that corresponds to the sample in the .log file with the maximum posterior probability.
"""
def extract_maximum_likelihood_tree(log_file, trees_file, output_file):
    # First, get the sample with the highest posterior probability:
    max_posterior = None
    max_posterior_sample = -1
    sample_col = -1
    posterior_col = -1
    with open(log_file, "r", encoding="utf-8") as f:
        i = 0
        for line in f:
            # Skip all lines that begin with "#":
            if line.startswith("#"):
                continue
            # The first line after this will contain column headers; get the indices of the "sample" and "posterior" columns:
            if i == 0:
                cols = line.split()
                sample_col = cols.index("Sample")
                posterior_col = cols.index("posterior")
                i += 1
                continue
            # Every subsequent line will contains the values for these columns at each sample, separated by tabs:
            vals = line.split()
            sample = int(vals[sample_col])
            posterior = float(vals[posterior_col])
            if max_posterior is None or posterior > max_posterior:
                max_posterior = posterior
                max_posterior_sample = sample
            i += 1
    # Then copy the desired parts of the input .trees file to the output .tree file:
    with open(output_file, "w", encoding="utf-8") as out:
        with open(trees_file, "r", encoding="utf-8") as f:
            for line in f:
                # Copy all lines that don't describe a sampled tree:
                if not line.startswith("tree STATE"):
                    out.write(line)
                    continue
                # Otherwise, get the sample number associated with this tree:
                tree_sample = int(line.split(" = ")[0].split("_")[1])
                # If its sample number matches the maximum-probability sample, then write this line to the output file and exit this loop:
                if tree_sample == max_posterior_sample:
                    out.write(line)
                    out.write("End;")
                    break
    return


"""
Entry point to the script. Parses command-line arguments and calls the core functions.
"""
def main():
    parser = argparse.ArgumentParser(description="Extracts the tree from a BEAST 2 .trees output file that corresponds to the sample from a BEAST 2 .log file with the maximum posterior probability.")
    parser.add_argument("log_file", type=str, help="The .log file containing the posterior probabilities of sampled states.")
    parser.add_argument("trees_file", type=str, help="The .trees file from which to extract the tree.")
    parser.add_argument("output_file", type=str, help="The .tree file to which to write the tree corresponding to the maximum probability.")
    args = parser.parse_args()
    # Parse the positional arguments:
    log_file = args.log_file
    trees_file = args.trees_file
    output_file = args.output_file
    extract_maximum_likelihood_tree(log_file, trees_file, output_file)
    exit(0)

if __name__=="__main__":
    main()