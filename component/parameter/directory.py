from pathlib import Path

__all__ = ['BASE_DIR', 'RAW_DIR', 'PROCESSED_DIR', 'STACK_DIR']
# Download folder


BASE_DIR = Path('~').expanduser()/'module_results/pysmm_downloads'
BASE_DIR.mkdir(parents=True, exist_ok=True)

RAW_DIR = BASE_DIR/'0_raw'
RAW_DIR.mkdir(parents=True, exist_ok=True)

PROCESSED_DIR = BASE_DIR/'1_processed'
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

STACK_DIR = BASE_DIR/'2_stack'
STACK_DIR.mkdir(parents=True, exist_ok=True)

