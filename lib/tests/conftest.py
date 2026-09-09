import sys
from pathlib import Path

# make `import lib.data` work no matter where pytest is invoked from
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "slow: end-to-end run over the real 1s data file (skipped if absent)"
    )
