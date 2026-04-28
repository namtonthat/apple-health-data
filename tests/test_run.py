from __future__ import annotations

import run


def test_run_all_stops_before_transform_when_ingest_fails(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(run, "load_env", lambda: calls.append("load_env"))
    monkeypatch.setattr(
        run,
        "run_ingest",
        lambda sources, date, strict=False: ["strava"],
    )
    monkeypatch.setattr(run, "run_transform", lambda: calls.append("transform"))
    monkeypatch.setattr(run, "run_export", lambda: calls.append("export"))

    try:
        run.run_all("2026-01-15")
    except RuntimeError as exc:
        assert "strava" in str(exc)
    else:
        raise AssertionError("run_all() should raise when ingest fails")

    assert calls == ["load_env"]


def test_main_ingest_exits_non_zero_when_a_source_fails(monkeypatch):
    monkeypatch.setattr(run, "_raise_fd_limit", lambda: None)
    monkeypatch.setattr(
        run,
        "run_ingest",
        lambda sources, date, strict=False: ["hevy"],
    )
    monkeypatch.setattr(
        run.argparse.ArgumentParser,
        "parse_args",
        lambda self: type("Args", (), {"stage": "ingest", "sources": ["hevy"], "date": None})(),
    )

    try:
        run.main()
    except SystemExit as exc:
        assert exc.code == 1
    else:
        raise AssertionError("main() should exit with code 1 when ingest fails")
