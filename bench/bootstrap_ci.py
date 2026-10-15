"""Bootstrap CI for the A/B geomean ratio.

Reads an ab_bench.py result JSON (with raw_A/raw_B), resamples rounds
with replacement, recomputes per-case median ratio + geomean each draw.
Usage: python3 bootstrap_ci.py <result.json> [draws]
"""
import json, sys, random, statistics, math

path = sys.argv[1]
draws = int(sys.argv[2]) if len(sys.argv) > 2 else 10000
D = json.load(open(path))
va, vb = D["raw_A"], D["raw_B"]
keys = list(D["medians_A"].keys())
n = len(va)
rng = random.Random(20261015)

def geo(ratios):
    return math.exp(sum(math.log(x) for x in ratios) / len(ratios))

def one_sample(idxs):
    ratios = []
    for k in keys:
        ma = statistics.median(va[i][k] for i in idxs)
        mb = statistics.median(vb[i][k] for i in idxs)
        ratios.append(mb / ma)
    return geo(ratios)

sims = [one_sample([rng.randrange(n) for _ in range(n)]) for _ in range(draws)]
sims.sort()
obs = one_sample(list(range(n)))
lo = sims[int(0.025 * draws)]
hi = sims[int(0.975 * draws) - 1]
print(f"observed geomean = {obs:.4f}")
print(f"bootstrap 95% CI = [{lo:.4f}, {hi:.4f}]  ({draws} draws)")
print(f"interpretation: CI {'excludes' if hi < 1 else 'includes'} 1.0 -> B {'significantly faster' if hi < 1 else 'not separable from noise'}")
