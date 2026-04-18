"""Tests for the integration pipeline."""
import os
from pathlib import Path

import pytest


class TestSiblingDiscovery:
    def test_sibling_repos_registered(self):
        from src.pipeline.integrator import SIBLING_REPOS
        assert "trendline-detector" in SIBLING_REPOS
        assert "backtest-lab" in SIBLING_REPOS

    def test_each_entry_has_github_url(self):
        from src.pipeline.integrator import SIBLING_REPOS
        for name, cfg in SIBLING_REPOS.items():
            assert "github" in cfg
            assert cfg["github"].startswith("https://github.com/")

    def test_find_sibling_via_env_var(self, tmp_path, monkeypatch):
        """Env var pointing to parent dir should be honored."""
        from src.pipeline.integrator import find_sibling_repo

        # Make a fake sibling repo
        sibling = tmp_path / "trendline-detector"
        (sibling / "src").mkdir(parents=True)
        (sibling / "src" / "__init__.py").write_text("")

        monkeypatch.setenv("CHART_ANALYZER_SIBLING_PATH", str(tmp_path))
        result = find_sibling_repo("trendline-detector", auto_clone=False)
        assert result.resolve() == sibling.resolve()

    def test_find_sibling_unknown_name_raises(self):
        from src.pipeline.integrator import find_sibling_repo
        with pytest.raises(ValueError, match="Unknown sibling"):
            find_sibling_repo("nonexistent-repo", auto_clone=False)

    def test_find_sibling_not_found_raises_with_hints(self, tmp_path, monkeypatch):
        from src.pipeline.integrator import find_sibling_repo
        # Point to an empty dir
        monkeypatch.setenv("CHART_ANALYZER_SIBLING_PATH", str(tmp_path))
        with pytest.raises(FileNotFoundError, match="Could not find"):
            find_sibling_repo("trendline-detector", auto_clone=False)


class TestIntegratorSmoke:
    """Smoke test using real sibling repos in /home/claude/newrepos.

    Will skip if siblings not present.
    """
    def _has_siblings(self) -> bool:
        try:
            from src.pipeline.integrator import find_sibling_repo
            find_sibling_repo("trendline-detector", auto_clone=False)
            find_sibling_repo("backtest-lab", auto_clone=False)
            return True
        except Exception:
            return False

    def test_run_detection_if_siblings_available(self):
        if not self._has_siblings():
            pytest.skip("Sibling repos not found")
        from src.pipeline.integrator import run_detection
        result = run_detection("SPY", days=60)
        assert "ticker" in result
        assert "swings" in result
        assert len(result["swings"]) > 0

    def test_format_caption_with_empty_result(self):
        from src.pipeline.integrator import _format_pipeline_caption
        combined = {"ticker": "TEST"}
        caption = _format_pipeline_caption(combined)
        assert "TEST" in caption
        assert len(caption) <= 1000

    def test_format_caption_truncates_long_content(self):
        from src.pipeline.integrator import _format_pipeline_caption
        combined = {
            "ticker": "LONG",
            "analysis": {"reasoning": "x" * 5000},
        }
        caption = _format_pipeline_caption(combined)
        assert len(caption) <= 1000
