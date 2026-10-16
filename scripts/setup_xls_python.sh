#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON="${PYTHON:-python3}"
"$PYTHON" -m venv "$ROOT/.venv"
"$ROOT/.venv/bin/python" -m pip install --disable-pip-version-check -r "$ROOT/scripts/requirements-xls.txt"
"$ROOT/.venv/bin/python" -c 'import xlrd; assert xlrd.__version__ == "2.0.2"; print("XLS converter ready: xlrd", xlrd.__version__)'
printf '%s\n' "CMS .env: MUSEUM_XLS_PYTHON=$ROOT/.venv/bin/python"
