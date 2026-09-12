import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.config import ROOT, settings
from backend.app.ingestion import digest

if __name__ == '__main__':
    jar = ROOT / '.cache/tika-app.jar'
    if not jar.exists():
        raise SystemExit('Install Java 17+ and download tika-app-3.2.3.jar to .cache/tika-app.jar (see README).')
    for source in settings.corpus.rglob('*.ppt'):
        target = ROOT / 'data/converted' / digest(source)
        subprocess.run(['java', '-Djava.awt.headless=true', '-cp', str(jar), str(ROOT / 'scripts/LegacySlides.java'), str(source), str(target)], check=True, timeout=180)
