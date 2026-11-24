"""Self-test: the scripts must recover the values put into the synthetic files (make_test_data.py).

Run: python tools/measure/test_measure.py   (exit code 0 = all good)
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import make_test_data  # noqa: E402
import report  # noqa: E402


def main() -> int:
    d = Path(tempfile.mkdtemp(prefix="st_measure_"))
    truth = make_test_data.main(d)
    res = {(r.test, r.quantity): r for r in report.run_folder(d)}

    def get(q):
        for (t, qq), r in res.items():
            if qq.startswith(q):
                return r
        raise KeyError(q)

    checks = [
        ("encoder noise", get("encoder noise").value, truth["noise_rms"], 0.01),
        ("periodic error", get("raw periodic error").value, truth["pe_half_pp"], 0.5),
        ("lost motion raw", get("lost motion raw").value, truth["lm_raw"], 0.5),
        ("lost motion loop", get("lost motion with encoder loop").value, truth["lm_loop"], 0.5),
        ("PEC left", get("left with PEC playing").value, truth["pec_left"], 0.15),
        ("map residual", get("residual of the map itself").value, 4.0, 0.3),
        ("sweep p-p", get("raw linearity").value, truth["sweep_pp"], 0.5),
        ("emulated map residual", get("residual after a map").value, 2.0, 0.3),
    ]
    bad = 0
    for name, got, want, tol in checks:
        ok = abs(got - want) <= tol
        bad += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {name}: got {got:.3f}, put in {want:.3f} (tolerance {tol})")
    verdicts = [r.verdict for r in res.values()]
    print(f"{len(res)} results, verdicts: " + json.dumps({v: verdicts.count(v) for v in set(verdicts)}))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
