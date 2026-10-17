"""A failed rerun must not retain an earlier success receipt."""

import json

import pandas as pd
import pytest

from scripts import reproduce


def test_parquet_engine_roundtrip(tmp_path):
    path = tmp_path / "roundtrip.parquet"
    expected = pd.DataFrame({"station_id": ["a", "b"], "value": [1.0, 2.0]})
    expected.to_parquet(path, index=False)
    actual = pd.read_parquet(path)
    pd.testing.assert_frame_equal(actual, expected)


def test_failed_step_replaces_old_pass(monkeypatch, tmp_path):
    receipt = tmp_path / "receipt.json"
    receipt.write_text('{"status": "PASS"}', encoding="utf-8")
    monkeypatch.setattr(reproduce, "RECEIPT", receipt)
    monkeypatch.setattr(reproduce.sys, "argv", ["reproduce", "--mode", "derived"])
    monkeypatch.setattr(reproduce, "verify_derived_inputs", lambda: 1)
    monkeypatch.setattr(reproduce, "derived_steps", lambda: [("broken step", ["dummy"])])

    def fail(*args):
        raise SystemExit(7)

    monkeypatch.setattr(reproduce, "run_step", fail)
    with pytest.raises(SystemExit):
        reproduce.main()
    result = json.loads(receipt.read_text(encoding="utf-8"))
    assert result["status"] == "FAILED"
    assert result["active_step"] == "broken step"
    assert result["steps"] == []
