"""Tests for the unattended run in update.py; every subprocess is replaced, nothing touches git."""

from types import SimpleNamespace

import update


def test_failed_push_fails_the_pipeline_and_names_the_step(monkeypatch, tmp_path, capsys):
    ok, refused = SimpleNamespace(returncode=0), SimpleNamespace(returncode=128)
    monkeypatch.setattr(update, "ERROR_FILE", str(tmp_path / "error.log"))
    monkeypatch.setattr(update, "load_token", lambda: "token")
    monkeypatch.setattr(update, "update_readme_badge", lambda count: None)
    monkeypatch.setattr(update, "run", lambda args: ok)
    monkeypatch.setattr(update, "git_authenticated", lambda args, token: refused if args[0] == "push" else ok)
    update.main()
    out = capsys.readouterr().out
    assert "ERROR: git push failed (exit code 128)" in out
    assert out.rstrip().endswith("=== PIPELINE FAILED: 0 error(s), failed step(s): git push ===")
