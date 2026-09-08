from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def test_demo_pipeline():
    r=subprocess.run([sys.executable,str(ROOT/'scripts/ficool.py'),'demo','máy lạnh bị chảy nước'],cwd=ROOT,capture_output=True,text=True)
    assert r.returncode==0,r.stderr
    out=ROOT/'output/demo/may-lanh-bi-chay-nuoc'
    assert (out/'article.md').exists(); assert (out/'article.html').exists(); assert (out/'demo.yaml').exists()
