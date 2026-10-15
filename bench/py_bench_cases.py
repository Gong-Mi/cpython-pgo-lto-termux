"""Benchmark cases. Prints one JSON object: {case: cpu_seconds}.
CPU time (time.process_time, user+sys of this process) is the metric —
wall time on a phone conflates dvfs/thermal/scheduling noise.

Usage: python3 py_bench_cases.py [reps]
"""
import timeit, json, sys, time

reps = int(sys.argv[1]) if len(sys.argv) > 1 else 5
T = time.process_time
R = {}

R["float_loop"] = timeit.timeit(
    "s=0.0\nfor i in range(100000):\n    s+=i*1.5", number=reps, timer=T) / reps
R["call_overhead"] = timeit.timeit(
    "f()", setup="def f(): return 1", number=200000, timer=T) / 200000
R["list_comp"] = timeit.timeit(
    "[i*i for i in range(100000)]", number=reps, timer=T) / reps
R["str_utf8"] = timeit.timeit(
    "s.encode('utf-8')", setup="s='中文测试'*1000", number=1000, timer=T) / 1000
data = {"a": list(range(100)), "b": "x"*500, "c": [1.5, 2.5]*50}
R["json_roundtrip"] = timeit.timeit(
    "import json; json.dumps(d); json.loads(t)",
    setup=f"d={data!r}; import json; t=json.dumps(d)", number=1000, timer=T) / 1000
R["regex"] = timeit.timeit(
    "p.sub('', s)",
    setup="import re; p=re.compile(r'[0-9]+'); s='abc123def456'*1000",
    number=100, timer=T) / 100
R["dict_build"] = timeit.timeit(
    "{i: i for i in range(100000)}", number=reps, timer=T) / reps

print(json.dumps(R))
