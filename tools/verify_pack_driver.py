"""verify_pack driver — sub-checks b-g of the packed-runtime gate.

Run BY THE PACKED python.exe with cwd = <pack>/engine (so `techniques`
resolves against the PACKED tree, never the dev tree). Each sub-check exits
0 on pass, 1 on fail, printing the evidence it gates on.
"""
import json
import os
import struct
import subprocess
import sys
import tempfile
import time

# The embeddable runtime's ._pth pins sys.path (cwd is NOT importable by
# default); cwd is the PACKED engine dir, so make `techniques` resolvable.
sys.path.insert(0, os.getcwd())

import numpy as np


def _mk_request(technique_id, n=120, params=None, seed=42):
    import pandas as pd
    rng = np.random.default_rng(seed)
    vals = np.cumsum(rng.standard_normal(n)).tolist()
    times = pd.date_range("2020-01-01", periods=n, freq="D").strftime(
        "%Y-%m-%d").tolist()
    return {
        "run_id": f"verify_{technique_id}",
        "technique_id": technique_id,
        "preset": "Fast",
        "seed": seed,
        "frequency": "D",
        "time": times,
        "series": [{"name": "verify_series", "values": vals}],
        "params": params or {},
    }


def _run_technique(technique_id, params=None):
    from techniques.base import RunContext
    from techniques.registry import TECHNIQUE_REGISTRY
    import importlib

    module_path = TECHNIQUE_REGISTRY[technique_id]
    mod = importlib.import_module(module_path)
    ctx = RunContext(_mk_request(technique_id, params=params))
    return mod.run(ctx, lambda *a, **k: None)


def check_classical():
    resp = _run_technique("adf_test")
    status = resp.get("status")
    n_tables = len(resp.get("tables") or [])
    print(f"adf_test: status={status}, tables={n_tables}")
    return status == "success" and n_tables > 0


def check_workbook():
    import openpyxl  # noqa: F401 - the P-D1 class proof
    import pandas as pd

    path = os.path.join(tempfile.mkdtemp(prefix="tsl_verify_"), "wb.xlsx")
    pd.DataFrame({"Date": ["2024-01-01", "2024-01-02"], "Y": [1.5, 2.5]}).to_excel(
        path, index=False)
    back = pd.read_excel(path)
    ok = list(back.columns) == ["Date", "Y"] and float(back["Y"].iloc[1]) == 2.5
    print(f"openpyxl {openpyxl.__version__}: write+read roundtrip ok={ok}")
    return ok


def check_numba():
    import numba
    print(f"numba {numba.__version__} imports")
    from techniques.bond_yield_forecast._jit_warmer import warm_jit_caches
    t0 = time.perf_counter()
    warm_jit_caches()  # raises on compile failure
    print(f"BYF JIT warmer compiled in {time.perf_counter() - t0:.1f}s")
    return True


def check_prophet():
    try:
        from prophet import Prophet
    except ImportError:
        # honest-degrade path: the technique must still run and disclose
        resp = _run_technique("prophet_forecast")
        blob = json.dumps(resp).lower()
        disclosed = "naive" in blob or "fallback" in blob or "prophet not" in blob
        print(f"prophet ABSENT; technique status={resp.get('status')}, "
              f"degradation disclosed={disclosed}")
        return resp.get("status") == "success" and disclosed
    import pandas as pd
    df = pd.DataFrame({
        "ds": pd.date_range("2020-01-01", periods=60, freq="D"),
        "y": np.sin(np.arange(60) / 5.0) + np.arange(60) * 0.05,
    })
    m = Prophet()
    m.fit(df)
    fc = m.predict(m.make_future_dataframe(periods=5))
    ok = len(fc) == 65 and np.isfinite(fc["yhat"].to_numpy()).all()
    print(f"prophet fit+predict ok={ok} (65 rows, finite yhat)")
    return ok


def check_dl():
    try:
        import torch  # noqa: F401
        print("UNEXPECTED: torch present in the packed runtime (DP2 excludes it)")
        return False
    except ImportError:
        pass
    resp = _run_technique("transformer_forecast", params={"epochs": 2})
    if resp.get("status") != "success":
        print(f"transformer_forecast failed: {resp.get('error_message')}")
        return False
    blob = json.dumps(resp).lower()
    # the fallback must be VISIBLY disclosed in the technique OUTPUT
    # (silent degradation = a labeling defect -> gate red)
    disclosed = ("sklearn" in blob or "mlpregressor" in blob
                 or "fallback" in blob)
    print(f"torch absent; sklearn fallback disclosed in output={disclosed}")
    return disclosed


def check_pipe():
    pipe_name = f"TSL_VERIFY_{os.getpid()}"
    worker = subprocess.Popen(
        [sys.executable, "engine_worker.py", "--pipe", pipe_name],
        cwd=os.getcwd(), stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    try:
        pipe_path = rf"\\.\pipe\{pipe_name}"
        handle = None
        for _ in range(50):  # up to 5 s for the server to listen
            try:
                handle = open(pipe_path, "r+b", buffering=0)
                break
            except OSError:
                time.sleep(0.1)
        if handle is None:
            print("pipe never became connectable")
            return False
        req = json.dumps(_mk_request("adf_test")).encode("utf-8")
        handle.write(struct.pack("<I", len(req)) + req)
        # read framed messages until the RunResponse (progress events first)
        deadline = time.time() + 120
        status = None
        while time.time() < deadline:
            hdr = handle.read(4)
            if len(hdr) < 4:
                break
            (mlen,) = struct.unpack("<I", hdr)
            body = json.loads(handle.read(mlen).decode("utf-8"))
            if body.get("type") == "progress":
                continue
            status = body.get("status")
            break
        handle.close()
        print(f"pipe smoke: served one request, RunResponse status={status}")
        ok = status == "success"
    finally:
        worker.kill()
    _, err = worker.communicate(timeout=30)
    if b"Traceback" in (err or b""):
        print("worker stderr contained a Traceback:")
        print((err or b"").decode("utf-8", "replace")[-2000:])
        return False
    return ok


CHECKS = {
    "classical": check_classical,
    "workbook": check_workbook,
    "numba": check_numba,
    "prophet": check_prophet,
    "dl": check_dl,
    "pipe": check_pipe,
}

if __name__ == "__main__":
    name = sys.argv[1]
    try:
        ok = CHECKS[name]()
    except Exception as e:  # noqa: BLE001 - gate reports, never masks
        import traceback
        traceback.print_exc()
        print(f"[{name}] EXCEPTION: {e}")
        ok = False
    sys.exit(0 if ok else 1)
