from fractions import Fraction

TO_RUN = [("~/PrIC3/Benchmarks_CAV/brp_small.pm", 1066, [0.005,0.01,0.02,0.03,0.035,0.0354, 0.036, 0.038, 0.04, 0.08,0.1,0.2,0.3,0.4,0.5]),
          ("~/PrIC3/Benchmarks_CAV/brp_medium.pm", 10305,[0.00005,0.0001,0.0002, 0.0003, 0.000379, 0.0004, 0.00045, 0.0005, 0.001, 0.002, 0.003, 0.005, 0.01, 0.05, 0.1]), \
          ("~/PrIC3/Benchmarks_CAV/brp_gigantic.pm", 2.8*10**6,[0.1,0.2,0.3,0.35,0.37,0.38,0.387,0.3879,0.39,0.4,0.42,0.44,0.46,0.48,0.5,0.6,0.7,0.8])] \
    \
  + [("~/PrIC3/Benchmarks_CAV/zero_conf_small.pm", 1003,[0.2, 0.3, 0.4, 0.45, 0.5,0.52,0.54,0.56,0.6,0.65,0.7, 0.75, 0.8, 0.9]),
     ("~/PrIC3/Benchmarks_CAV/zero_conf_medium.pm", 10000,[0.2, 0.3, 0.4, 0.45, 0.5,0.52,0.54,0.56,0.6,0.65,0.7, 0.75, 0.8, 0.9]),
     ("~/PrIC3/Benchmarks_CAV/zero_conf_gigantic.pm", 10**8,[0.2, 0.3, 0.4, 0.45, 0.5,0.52,0.54,0.56,0.6,0.65,0.7, 0.75, 0.8, 0.9]),
     ("~/PrIC3/Benchmarks_CAV/zero_conf_gigantic_2.pm", 10**9,[0.2, 0.3, 0.4, 0.45, 0.5,0.52,0.54,0.56,0.6,0.65,0.7, 0.75, 0.8, 0.9])] \
    \
  + [("~/PrIC3/Benchmarks_CAV/haddad_monmege_small.pm", 1003,[0.2, 0.3, 0.4, 0.45, 0.5,0.52,0.54,0.56,0.6,0.65,0.7,0.8,0.9]),
     ("~/PrIC3/Benchmarks_CAV/haddad_monmege_medium.pm", 10003,[0.2, 0.3, 0.4, 0.45, 0.5,0.52,0.54,0.56,0.6,0.65,0.7,0.8,0.9]),
     ("~/PrIC3/Benchmarks_CAV/haddad_monmege_gigantic.pm", 10**8,[0.2, 0.3, 0.4, 0.45, 0.5,0.52,0.54,0.56,0.6,0.65,0.7,0.8,0.9])] \
    \
  + [("~/PrIC3/Benchmarks_CAV/chain_small.pm", 1001, [0.3,0.35,0.39,0.393,0.3937, 0.4, 0.42, 0.44, 0.46, 0.48, 0.5, 0.55, 0.6,0.65,0.7,0.8,0.9]),
     ("~/PrIC3/Benchmarks_CAV/chain_medium.pm", 10001, [0.3,0.35,0.39,0.393,0.3936, 0.4, 0.42, 0.44, 0.46, 0.48, 0.5, 0.55, 0.6,0.65,0.7,0.8,0.9]),
     ("~/PrIC3/Benchmarks_CAV/chain_gigantic.pm", 10**12, [0.3,0.35,0.39,0.393,0.3936, 0.4, 0.42, 0.44, 0.46, 0.48, 0.5, 0.55, 0.6,0.65,0.7,0.8,0.9])] \
    \
  + [("~/PrIC3/Benchmarks_CAV/double_chain_small.pm", 1002, [0.05,0.1,0.15,0.2,0.21,0.216,0.217,0.218,0.219,0.3,0.32,0.34,0.36,0.38,0.4,0.5,0.55,0.6,0.7]),
     ("~/PrIC3/Benchmarks_CAV/double_chain_medium.pm", 10002, [0.05,0.1,0.15,0.2,0.24,0.25,0.26,0.27, 0.28, 0.29,0.3, 0.35,0.4,0.45,0.5,0.6,0.7]),
     ("~/PrIC3/Benchmarks_CAV/doubel_chain_gigantic.pm", 10**7, [0.00005,0.0001,0.00015,0.0002,0.00027,0.00028,0.00029,0.003,0.004,0.005,0.006,0.01,0.015,0.2,0.25,0.3,0.4,0.5,0.6,0.7])]
# \
# + [("~/PrIC3/Benchmarks_CAV/grid_small.pm", 1088, [0.00001,0.00005,0.0001,0.0002,0.00027,0.00028,0.00029,0.0003,0.0005,0.001,0.005,0.01,0.05,0.1,0.2,0.3,0.4,0.5]),
#    ("~/PrIC3/Benchmarks_CAV/grid_medium.pm", 10200, [0.00001,0.00005,0.0001,0.0002,0.0004,0.00044,0.00045,0.0005,0.00055,0.0006,0.0007,0.0008,0.0009,0.001,0.002,0.003,0.005,0.01,0.0,0.05,0.1,0.2,0.3,0.5,0.9]),
#    ("~/PrIC3/Benchmarks_CAV/grid_gigantic.pm", 10**8,[0.2, 0.3, 0.4, 0.45, 0.5,0.52,0.54,0.56,0.6,0.65,0.7,0.8,0.9])]
CONFIGS = [
    ("nogen",
     "--oracle-type solveeqspartly_inexact --depth-for-partly-solving-lqs %s --forall-mode macro --no-generalize"
     ),
    ("nogen",
     "--oracle-type solveeqspartly_inexact --depth-for-partly-solving-lqs %s --forall-mode globals --no-generalize"
     ),
    ("nogen",
     "--oracle-type solveeqspartly_inexact --depth-for-partly-solving-lqs %s --forall-mode globals --no-generalize --int-to-real"
     ),
    ("oracleperfect",
     "--oracle-type solveeqspartly_inexact --depth-for-partly-solving-lqs %s --forall-mode globals --generalize --generalization-method Linear --int-to-real --max-num-ctgs 0"
     ),
    ("oracleperfect",
     "--oracle-type solveeqspartly_inexact --depth-for-partly-solving-lqs %s --forall-mode globals --generalize --generalization-method Linear --int-to-real --max-num-ctgs 1"
     ),
    ("oracleperfect",
     "--oracle-type solveeqspartly_inexact --depth-for-partly-solving-lqs %s --forall-mode globals --generalize --generalization-method Linear --int-to-real --max-num-ctgs 2"
     ),
    ("oracleperfect",
     "--oracle-type solveeqspartly_inexact --depth-for-partly-solving-lqs %s --forall-mode globals --generalize --generalization-method Hybrid --int-to-real --max-num-ctgs 0"
     ),
    ("oracleperfect",
     "--oracle-type solveeqspartly_inexact --depth-for-partly-solving-lqs %s --forall-mode globals --generalize --generalization-method Hybrid --int-to-real --max-num-ctgs 1"
     ),
    ("oracleperfect",
     "--oracle-type solveeqspartly_inexact --depth-for-partly-solving-lqs %s --forall-mode globals --generalize --generalization-method Hybrid --int-to-real --max-num-ctgs 2"
     ),
    ("oracleperfect",
     "--oracle-type solveeqspartly_inexact --depth-for-partly-solving-lqs %s --forall-mode globals --generalize --generalization-method Polynomial --int-to-real --max-num-ctgs 0"
     ),
    ("oracleperfect",
     "--oracle-type solveeqspartly_inexact --depth-for-partly-solving-lqs %s --forall-mode globals --generalize --generalization-method Polynomial --int-to-real --max-num-ctgs 1"
     ),
    ("oracleperfect",
     "--oracle-type solveeqspartly_inexact --depth-for-partly-solving-lqs %s --forall-mode globals --generalize --generalization-method Polynomial --int-to-real --max-num-ctgs 2"
     ),
]


REPEAT_COUNT = 3

COMMANDS = []
for model, num_states, lams in TO_RUN:
    for lam in lams:
        for (conf_name, conf) in CONFIGS:
            for i in range(REPEAT_COUNT):
                COMMANDS.append(
                    "python3 ~/PrIC3/pric3.py %s --lam %s %s --save-stats --tag %s"
                    % (model, lam,
                       (conf % str(min(num_states, 5000))), conf_name))

with open('jobs.txt', 'w') as f:
    jobs = ["timeout -s TERM 900 %s" % cmd for cmd in COMMANDS]
    f.write("\n".join(jobs))

with open('job.sh.template', 'r') as f:
    with open('job.sh', 'w') as f2:
        f2.write(f.read().replace('%%NUMBER_OF_JOBS%%', str(len(COMMANDS))))
