"""A/B benchmark harness: stock Termux python vs PGO+LTO build.

Interleaves A/B runs round-robin to cancel thermal/dvfs drift,
reports per-case median and overall geomean ratio.
"""
import subprocess, sys, time, json, statistics, math, os, shlex

BENCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "py_bench_cases.py")
WRAP = shlex.split(os.environ.get("WRAP", ""))

def run_one(python, reps=5):
    out = subprocess.run(WRAP + [python, BENCH, str(reps)], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)

def main():
    python_a = sys.argv[1]  # stock
    python_b = sys.argv[2]  # pgo+lto
    rounds = int(sys.argv[3]) if len(sys.argv) > 3 else 7
    label_a, label_b = sys.argv[4], sys.argv[5]

    va, vb = [], []
    for r in range(rounds):
        va.append(run_one(python_a))
        vb.append(run_one(python_b))
        print(f"round {r+1}/{rounds} done", file=sys.stderr)

    keys = va[0].keys()
    ratios = []
    print(f"{'case':16s} {'A '+label_a:>12s} {'B '+label_b:>12s} {'B/A':>8s}")
    for k in keys:
        ma = statistics.median(x[k] for x in va)
        mb = statistics.median(x[k] for x in vb)
        ratios.append(mb / ma)
        print(f"{k:16s} {ma*1000:10.3f}ms {mb*1000:10.3f}ms {mb/ma:8.3f}")
    geo = math.exp(sum(math.log(x) for x in ratios) / len(ratios))
    print(f"\ngeomean B/A = {geo:.3f}  (<1 means B faster)")
    print(json.dumps({"A": label_a, "B": label_b, "rounds": rounds,
                      "medians_A": {k: statistics.median(x[k] for x in va) for k in keys},
                      "medians_B": {k: statistics.median(x[k] for x in vb) for k in keys},
                      "geomean_ratio": geo,
                      "raw_A": va, "raw_B": vb}))

if __name__ == "__main__":
    main()
