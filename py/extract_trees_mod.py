#!/usr/bin/env python3

import argparse

"""
Given a .trees file address, an output .trees file address, and an integer i,
writes the contents of the input file to the output file, taking only every i-th tree.
"""
def extract_trees_mod(input_file, output_file, i=1):
    with open(output_file, "w", encoding="utf-8") as out_file:
        with open(input_file, "r") as in_file:
            parsing_trees = False
            tree_number = 0
            for line in in_file:
                # If we are already parsing the trees block, 
                # then only copy over this tree if is an i-th tree:
                if parsing_trees:
                    if tree_number % i == 0:
                        out_file.write(line)
                    tree_number += 1
                    continue
                # Otherwise, copy over the current line unconditionally, 
                # and if the current line has a tree, then set the parsing trees flag:
                out_file.write(line)
                if line.strip().startswith("tree"):
                    parsing_trees = True
                    tree_number += 1
    return

"""
Entry point to the script. Parses command-line arguments and calls the core functions.
"""
def main():
    parser = argparse.ArgumentParser(description="Copy the contents of the input .trees file to the output .trees file, taking only every i-th tree.")
    parser.add_argument("input_file", type=str, help="Input .trees file.")
    parser.add_argument("output_file", type=str, help="Output .trees file.")
    parser.add_argument("i", type=int, help="Sampling modulus for trees. Must be at least 1.")
    # Parse the command-line arguments:
    args = parser.parse_args()
    input_file = args.input_file
    output_file = args.output_file
    i = args.i
    # Do not allow moduli lower than 1:
    if i < 1:
        print("ERROR: sampling modulus must be at least 1.")
        exit(1)
    # Then process the file:
    extract_trees_mod(input_file, output_file, i)
    exit(0)

if __name__=="__main__":
    main()