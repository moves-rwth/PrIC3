# PrIC3 CAV Artifact

This Docker image contains the full PrIC3 code, and tools to generate three different benchmark tables.

Note: There is a quick introduction to Docker below the next section.

## Generating benchmark tables

In the Docker container, you can run one of three scripts in `/root/artifact/benchmarks/cav/`:
```
cd artifact/benchmarks/cav
python3 table1.py
python3 table2.py
python3 table1_additional_results.py
```

After termination, there will be a path to a generated PDF file with the results.

**Important: Running only selected benchmarks:**
The above scripts may take **very long to complete**.
Each script has a `--selected` option, which only selects (hardcoded) benchmarks that we have found to terminate within the time and memory limits.
```
python3 table1.py --selected
```

Then, you can copy the generated PDF file to your host system to view it (outside of the container):
```
docker cp pric3:/root/artifact/benchmarks/cav/.../....pdf .
```

To run PrIC3 on a single benchmark, first enter the artifact directory:
```
cd /root/artifact/
```

Some help is provided by executing
```
python3 pric3.py --help
```

Different benchmarks require different settings.
We demonstrate how to execute the benchmarks shown in Table 1 and Table 2 by means of the Chain benchmark with 10^3 states.
Furthermore, we demonstrate how to reproduce the results shown in:

```
table1_additional_results.pdf
```

We provided these additional results in the rebuttal and will include them in the camera-ready version of the paper.

All corresponding PRISM files are located in the `Benchmarks_CAV` directory.

To execute the benchmarks from Table 1 (which coincide with the benchmarks given in `table1_additional_results.pdf`)  ...

... without generalization, execute:

```
python3 pric3.py --lam 0.9 Benchmarks_CAV/chain_small.pm --no-generalize --forall-mode globals --int-to-real --depth-for-partly-solving-lqs 1000 --oracle-type solveeqspartly_inexact
```

... with linear generalization, execute:

```
python3 pric3.py --lam 0.9 Benchmarks_CAV/chain_small.pm --generalize --generalization-method Linear --max-num-ctgs 0 --forall-mode globals --int-to-real --depth-for-partly-solving-lqs 1000 --oracle-type solveeqspartly_inexact
```

... with polynomial generalization, execute:

```
python3 pric3.py --lam 0.9 Benchmarks_CAV/chain_small.pm --generalize --generalization-method Polynomial --max-num-ctgs 2 --forall-mode globals --int-to-real --depth-for-partly-solving-lqs 1000 --oracle-type solveeqspartly_inexact
```

... with hybrid generalization, execute:

```
python3 pric3.py --lam 0.9 Benchmarks_CAV/chain_small.pm --generalize --generalization-method Hybrid --max-num-ctgs 2 --forall-mode globals --int-to-real --depth-for-partly-solving-lqs 1000 --oracle-type solveeqspartly_inexact
```

The setting

```
--depth-for-partly-solving-lqs i
```
has to be adapted individually for every benchmark. For the given benchmarks, we have chosen `i = min(#states in the model, 5000)`.


Executing the benchmarks provided in Table 2 works as for the benchmarks from Table 1.
The difference only difference is the setting

```
--oracle-type o
```

For oracle type 1, choose:
  `o = perfect`

For oracle type 2, choose:
  `o = simulation`

For oracle type 3, choose:
  `o = modelchecking`

The PRISM file for the ZeroConf benchmark is `zero_conf_small.pm`.
The PRISM file for the chain benchmark is `chain_small.pm`.
The PRISM file for the double chain benchmark is `double_chain_small.pm`.



## Running Storm

To execute the storm benchmarks, first enter the artifact directory:
```
cd /root/artifact/
```

We describe how to generate the runtimes for  Storm Sparse and Storm DD depicted in Table 1 by means of the
```
Benchmarks_CAV/chain_small.pm
```
file.

To run the benchmark for Storm Sparse, execute:
```
deps/storm/build/bin/storm --prism "Benchmarks_CAV/chain_small.pm" --prop "P=? [F \"goal\"]"
```

To run the benchmark for Storm DD, execute:
```
deps/storm/build/bin/storm --prism "Benchmarks_CAV/chain_small.pm" --prop "P=? [F \"goal\"]" -e dd
```




Remark: By reviewer request, we will add the runtimes for the storm benchmarks *for every threshold*. This is not supported by our artifact at the current state. The results provided in the tables are obtained from the commands depicted above. These commands yield storm to compute the probability to reach a goal state (in contrast to checking an upper bound), which is the reason why they are independent of the threshold. Prior to submission, we consulted with some of Storm’s core developers and they reassured us that our comparison is fine for the purposes in this paper.

## General usage of Docker

**1. Loading the Docker image**

The Docker image is packaged as a compressed image.
To load it into your Docker installation, run:
```
docker load pric3.tar.gz
```

Now you have a `pric3` image which you can use for new containers.

**2. Enter a new container**

Create a new container named `pric3` based on the `pric3` image and enter it:
```
docker run -it --name pric3 pric3
```

<small>
Note: If you want to attach another shell session, you'll need to use the following command to enter the virtual environment:
```
docker exec -it pric3 "bash -c 'cd /root/ && source artifact/env_python/bin/activate && exec bash'"
```
</small>

**3. Copying files out of the container**

You can use the `docker cp pric3:/root/[FILE] [DEST_PATH]` command to copy files from the `pric3` container to your host system, e.g. to view the generated PDF files.
