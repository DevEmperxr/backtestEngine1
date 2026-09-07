import sys
from pathlib import Path

# make `import lib.data` work no matter where pytest is invoked from
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
