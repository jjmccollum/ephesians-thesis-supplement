import pandas as pd
import numpy as np
import argparse
import math
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.ticker import PercentFormatter
from matplotlib import rcParams
rcParams["font.family"] = "Georgia Pro"
rcParams.update({"font.size": 12})

parser = argparse.ArgumentParser(description="Makes a plot of the posterior distribution of a specified witness's age.")
parser.add_argument("--burnin", type=float, default=0.0, help="Burn-in proportion (must be a value between 0 and 1).")
parser.add_argument("input", help="The Beast 2 log file.")
parser.add_argument("output", help="The output file.")
parser.add_argument("witness", help="The ID of the witness whose age posterior distribution is desired.")

args = parser.parse_args()

# Parse the arguments:
input_addr = args.input
output_addr = args.output
witness = args.witness
burnin_pct = args.burnin

# 
column_label = "height(%s)" % witness

# Read the log file as if it were a TSV file:
df = pd.read_csv(input_addr, sep='\t', comment='#')
# Truncate the burn-in rows:
burnin = int(burnin_pct*len(df.index))
df = df.truncate(before=burnin)

fig, ax = plt.subplots(1, 1, figsize=(16, 5))
bin_width = 10
min_xlim = bin_width * math.floor(min(df[column_label]) / bin_width)
max_xlim = bin_width * math.ceil(max(df[column_label]) / bin_width)
bins = np.arange(min_xlim, max_xlim + bin_width, bin_width)
plt.hist(df[column_label], bins=bins, density=True, color="blue", edgecolor="black", alpha=0.5) # the histogram for the posterior distribution
# plt.axvline(df[column_label].mean(), color="blue", linestyle="dashed", linewidth=1) # the vertical line at the mean value
# mean_stddev_label = "%.2f $\pm$ %.2f" % (df[column_label].mean(), 2.0*df[column_label].std())
min_ylim, max_ylim = plt.ylim()
# plt.text(df[column_label].mean()+0.05, max_ylim*0.9, mean_stddev_label)

#leg = ax.legend()
ax.set_xlabel("Date")
ax.set_ylabel("Density")
#ax.set_xlim(0.0,20.0)
#plt.gca().yaxis.set_major_formatter(PercentFormatter(1))

plt.show()

fig.tight_layout()
fig.savefig(output_addr) 
print(f"Saved to {output_addr}")