from fractions import Fraction

TO_RUN = [("~/PrIC3/Benchmarks_CAV/brp_small.pm", [0.2, 0.3, 0.35, 0.4, 0.42, 0.44, 0.46, 0.48, 0.5, 0.55, 0.6, 0.7, 0,8]),
          ("~/PrIC3/Benchmarks_CAV/brp_medium.pm", [0.00001, 0.003 ,0.006, 0.009, 0.00982, 0.01, 0.015, 0.02, 0.03, 0.1, 0.2, 0.3]), \
          ("~/PrIC3/Benchmarks_CAV/brp_gigantic.pm", [0.1, 0.2, 0.3, 0.35, 0.387 , 0.3879, 0.4, 0.42, 0.44, 0.46, 0.5, 0.6,0.7, 0.8])] \
    \
  + [("~/PrIC3/Benchmarks_CAV/zero_conf_small.pm", [0.2, 0.3, 0.4, 0.45, 0.5,0.52,0.54,0.56,0.6,0.65,0.7, 0.75, 0.8, 0.9]),
     ("~/PrIC3/Benchmarks_CAV/zero_conf_medium.pm", [0.2, 0.3, 0.4, 0.45, 0.5,0.52,0.54,0.56,0.6,0.65,0.7, 0.75, 0.8, 0.9]),
     ("~/PrIC3/Benchmarks_CAV/zero_conf_gigantic.pm", [0.2, 0.3, 0.4, 0.45, 0.5,0.52,0.54,0.56,0.6,0.65,0.7, 0.75, 0.8, 0.9])] \
    \
  + [("~/PrIC3/Benchmarks_CAV/haddad_monmege_small.pm", [0.2, 0.3, 0.4, 0.45, 0.5,0.52,0.54,0.56,0.6,0.65,0.7,0.8,0.9]),
     ("~/PrIC3/Benchmarks_CAV/haddad_monmege_medium.pm", [0.2, 0.3, 0.4, 0.45, 0.5,0.52,0.54,0.56,0.6,0.65,0.7,0.8,0.9]),
     ("~/PrIC3/Benchmarks_CAV/haddad_monmege_gigantic.pm", [0.2, 0.3, 0.4, 0.45, 0.5,0.52,0.54,0.56,0.6,0.65,0.7,0.8,0.9])] \
    \
  + [("~/PrIC3/Benchmarks_CAV/chain_small.pm", [0.005,0.01,0.07,0.08,0.09, 0.095,0.0953, 0.1, 0.12, 0.14, 0.16, 0.2,0.3,0.4,0.5,0.6]),
     ("~/PrIC3/Benchmarks_CAV/chain_medium.pm", [0.2,0.3,0.4,0.45,0.5,0.55,0.6,0.63, 0.633, 0.64, 0.66, 0.68, 0.7, 0.75, 0.8, 0.85, 0.9]),
     ("~/PrIC3/Benchmarks_CAV/chain_gigantic.pm", [0.2,0.3,0.4,0.45,0.5,0.55,0.6,0.63, 0.633, 0.64, 0.66, 0.68, 0.7, 0.75, 0.8, 0.85, 0.9])] \
    \
  + [("~/PrIC3/Benchmarks_CAV/double_chain_small.pm", [0.005, 0.01,0.03,0.05,0.07, 0.08,0.088, 0.09, 0.095, 0.1, 0.15, 0.2, 0.25, 0.3, 0.5, 0.8]),
     ("~/PrIC3/Benchmarks_CAV/double_chain_medium.pm", [0.1, 0.2, 0.3, 0.35, 0.387 , 0.389, 0.4, 0.42, 0.44, 0.46, 0.5, 0.6,0.7, 0.8]),
     ("~/PrIC3/Benchmarks_CAV/doubel_chain_gigantic.pm", [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95])] \
  \
  + [("~/PrIC3/Benchmarks_CAV/grid_small.pm", [0.0001,0.001,0.005, 0.007, 0.009, 0.011, 0.01165, 0.012, 0.013, 0.014, 0.2, 0.25, 0.3, 0.35, 0.4, 0.8]),
     ("~/PrIC3/Benchmarks_CAV/grid_medium.pm", [0.001,0.01,0.05,0.1, 0.13,0.15,0.17, 0.172, 0.175, 0.18, 0.185, 0.19, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.8]),
     ("~/PrIC3/Benchmarks_CAV/grid_gigantic.pm", [0.2, 0.3, 0.4, 0.45, 0.5,0.52,0.54,0.56,0.6,0.65,0.7,0.8,0.9])]
CONFIGS = [
    ("nogen",
     "--oracle-type solveeqspartly --depth-for-partly-solving-lqs 1000 --forall-mode macro --no-generalize"
     ),
    ("oracleperfect",
     "--oracle-type solveeqspartly --depth-for-partly-solving-lqs 1000 --forall-mode globals --generalize --generalization-method Linear --int-to-real --max-num-ctgs 0"
     ),
    ("oracleperfect",
     "--oracle-type solveeqspartly --depth-for-partly-solving-lqs 1000 --forall-mode globals --generalize --generalization-method Linear --int-to-real --max-num-ctgs 1"
     ),
    ("oracleperfect",
     "--oracle-type solveeqspartly --depth-for-partly-solving-lqs 1000 --forall-mode globals --generalize --generalization-method Linear --int-to-real --max-num-ctgs 2"
     ),
    ("oracleperfect",
     "--oracle-type solveeqspartly --depth-for-partly-solving-lqs 1000 --forall-mode globals --generalize --generalization-method Hybrid --int-to-real --max-num-ctgs 0"
     ),
    ("oracleperfect",
     "--oracle-type solveeqspartly --depth-for-partly-solving-lqs 1000 --forall-mode globals --generalize --generalization-method Hybrid --int-to-real --max-num-ctgs 1"
     ),
    ("oracleperfect",
     "--oracle-type solveeqspartly --depth-for-partly-solving-lqs 1000 --forall-mode globals --generalize --generalization-method Hybrid --int-to-real --max-num-ctgs 2"
     ),
    ("oracleperfect",
     "--oracle-type solveeqspartly --depth-for-partly-solving-lqs 1000 --forall-mode globals --generalize --generalization-method Polynomial --int-to-real --max-num-ctgs 0"
     ),
    ("oracleperfect",
     "--oracle-type solveeqspartly --depth-for-partly-solving-lqs 1000 --forall-mode globals --generalize --generalization-method Polynomial --int-to-real --max-num-ctgs 1"
     ),
    ("oracleperfect",
     "--oracle-type solveeqspartly --depth-for-partly-solving-lqs 1000 --forall-mode globals --generalize --generalization-method Polynomial --int-to-real --max-num-ctgs 2"
     ),
]


REPEAT_COUNT = 3

COMMANDS = []
for model, lams in TO_RUN:
    for lam in lams:
        for (conf_name, conf) in CONFIGS:
            for i in range(REPEAT_COUNT):
                COMMANDS.append(
                    "python3 ~/PrIC3/pric3.py %s --lam %s %s --save-stats --tag %s"
                    % (model, lam, conf, conf_name))

with open('jobs.txt', 'w') as f:
    jobs = ["timeout -s TERM 900 %s" % cmd for cmd in COMMANDS]
    f.write("\n".join(jobs))

with open('job.sh.template', 'r') as f:
    with open('job.sh', 'w') as f2:
        f2.write(f.read().replace('%%NUMBER_OF_JOBS%%', str(len(COMMANDS))))

