import argparse
import yaml
from pathlib import os, Path
import pandas as pd
from functools import reduce

"""
Returns a DataFrame containing the root reading posterior probabilities, indexed by (variation unit, reading) tuples.
"""
def get_dataframe_from_yaml(yaml_file):
    df = None
    yaml_dict = {}
    with open(yaml_file, "r", encoding="utf-8") as f:
        yaml_dict = yaml.safe_load(f)
    # This should be a list, with an entry for each variation unit:
    index_tuples = []
    posteriors = []
    for vu in yaml_dict:
        posteriors_by_reading = yaml_dict[vu]
        for reading in posteriors_by_reading:
            posterior = posteriors_by_reading[reading]
            index_tuples.append((vu, reading))
            posteriors.append(posterior)
    # Generate a MultiIndex from the (variation unit, reading) tuples:
    base_filename = Path(yaml_file).stem
    index = pd.MultiIndex.from_tuples(index_tuples, names=["variation_unit", "reading"])
    df = pd.DataFrame(data=posteriors, columns=[base_filename], index=index)
    return df


"""
Entry point to the script. Parses command-line arguments and calls the core functions.
"""
def main():
    parser = argparse.ArgumentParser(description="Given the addresses of multiple .yaml files containing root reading posteriors, combines their contents into a spreadsheet with a column for each input file and writes this result to the given Excel output.")
    parser.add_argument("output", type=str, help="Output .xlsx file.")
    parser.add_argument("input", type=str, nargs="+", help="Input .yaml file(s) containing root reading posterior probabilities.")
    # Parse the command-line arguments:
    args = parser.parse_args()
    output = args.output
    inputs = args.input
    # Then extract each .yaml file's contents into a DataFrame with the (variation unit, reading) tuples forming a MultiIndex:
    dataframes = []
    for yaml_file in inputs:
        dataframes.append(get_dataframe_from_yaml(yaml_file))
    # Then merge these DataFrames along their indices:
    merged = reduce(lambda left, right: pd.merge(left, right, on=["variation_unit", "reading"], how="outer"), dataframes)
    # Then write to output:
    writer = pd.ExcelWriter(output, engine="xlsxwriter")
    merged.to_excel(writer, sheet_name="Comparison")
    # Then add formatting:
    workbook = writer.book
    worksheet = writer.sheets["Comparison"]
    percentage_format = workbook.add_format({"num_format": "0.00%"})
    for i in range(len(inputs)):
        worksheet.set_column(2+i, 2+i, None, percentage_format)
    # Close the Pandas Excel writer and output the Excel file.
    writer.close()
    exit(0)

if __name__=="__main__":
    main()