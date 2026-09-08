from pathlib import Path
import subprocess, sys

ROOT = Path(__file__).resolve().parents[1]

def test_demo_pipeline(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / "scripts/ficool.py"), "demo", "máy lạnh bị chảy nước"], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    out = ROOT / "output/runs/máy-lạnh-bị-chảy-nước"
    assert (out / "article.md").exists()
    assert (out / "image-manifest.json").exists()
    assert (out / "qa-report.json").exists()
