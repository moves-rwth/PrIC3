# Running PrIC3 on the RWTH cluster

The setup for benchmarks on the RWTH cluster is a bit of a challenge.

### Installation

Upload PrIC3 to `~/PrIC3` (we assume fixed paths for `hpc-scripts` and `PrIC3`).

```zsh
cd
git clone https://git.rwth-aachen.de/moves/hpc-scripts/

# GIT_USERNAME is your i2 SCM user name
zsh ~/PrIC3/benchmarks/build_stormpy.sh ~/stormpy GIT_USERNAME state-generator
ln -s ~/stormpy/env_python ~/env_python

cd ~/PrIC3
source benchmarks/prepare_environment.sh
source ~/env_python/bin/activate
pip3 install click pysmt pytest graphviz sphinx sphinx-click sphinx-bootstrap-theme sphinx_autodoc_typehints sphinx-git mypy pylint pandas
yes Y | pysmt-install --z3
```

Now everything should be in place to run the benchmark jobs.

### Running Benchmarks

To run benchmarks on the RWTH cluster, there are scripts in the `benchmarks/` directory.

1. Modify `generate_jobs.py` to appropiately generate benchmarks according to your needs.
2. Run the `generate_jobs.py` to generate `job.sh` and `jobs.txt` files for the cluster.
3. Create `~/output` directory for logs.
4. Submit `job.sh` to the job scheduler: `sbatch job.sh -A moves`.

Watch progress of the job: `watch squeue -u $USER`.

### Viewing Benchmark Results

Running PrIC3 with `--save-stats` (which `job.sh` does) will generate statistics in the `stats` directory.
You can then play with all generated statistics as follows (e.g. in [jupyter](https://jupyter.org/)):

```python
import numpy as np
import pandas as pd
import seaborn as sns
from pric3.statistics import *

# how many rows/columns to show
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', 5)

data = load_all_statistics("stats")
tt = statistics_to_pandas(data)

# for when you have multiple runs: average over same parameters.
# pass a list of attributes you want to average.
tt = average_pandas_statistics(tt, ['total_time'])

# filter and modify data table
tt = tt[tt['args.tag'] == 'generalize'] # the config name is saved in 'args.tag', here we filter for 'generalize'

# show the data table
display(tt)

# show the plot
plot = sns.lineplot(data=tt, x="args.lam", y="total_time", style="property_holds", hue="property_holds")
display(plot)
```

All program arguments are included in the pickle file (`args.[something]`) and can be filtered upon.
The path of the analysed program is saved as `args.program`.
Additionally, if PrIC3 was started with the benchmark script (`benchmarks/job.sh`), the task index is saved in `args.slurm_array_task_id`.
