#!/usr/bin/env python3
"""Read-only npm supply-chain gate. Never run npm audit fix or mutate lockfile.

The only exception is an unpatched *development-only* braces advisory in
Next 16's ESLint chain. Any new advisory, including another dev-only one,
fails closed. A genuinely patched tree automatically passes without exception.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'apps/web'
CHAIN = {'eslint-config-next', '@next/eslint-plugin-next', 'fast-glob', 'micromatch', 'braces'}
ADVISORY = 'https://github.com/advisories/GHSA-vfj7-8cjw-p6xm'


def validate(production: dict, full: dict) -> dict:
    prod = production.get('vulnerabilities')
    all_vulns = full.get('vulnerabilities')
    if not isinstance(prod, dict) or not isinstance(all_vulns, dict):
        raise ValueError('npm audit did not return an authoritative vulnerability inventory')
    if prod:
        raise ValueError('Production dependencies contain advisories: '+', '.join(sorted(prod)))
    if not all_vulns:
        return {'production_advisories': 0, 'dev_advisories': 0, 'exception': None}
    if set(all_vulns) != CHAIN:
        raise ValueError('Unexpected development dependency advisories: '+', '.join(sorted(set(all_vulns)^CHAIN)))
    for name, issue in all_vulns.items():
        if issue.get('severity') != 'high':
            raise ValueError('Changed dev advisory severity for '+name)
    root = all_vulns['braces']
    if len(root.get('via', [])) != 1 or not isinstance(root['via'][0], dict) or root['via'][0].get('url') != ADVISORY:
        raise ValueError('Unrecognized or additional braces advisory')
    for name, issue in all_vulns.items():
        if name != 'braces' and any(isinstance(v, dict) for v in issue.get('via', [])):
            raise ValueError('Additional upstream security issue in '+name)
    # npm graph must remain an isolated lint-only chain, NEVER production.
    if all_vulns['eslint-config-next'].get('isDirect') is not True:
        raise ValueError('Unexpected direct dependency relationship')
    if any(issue.get('isDirect') is True for n,issue in all_vulns.items() if n != 'eslint-config-next'):
        raise ValueError('Unexpected direct use of vulnerable development package')
    return {'production_advisories': 0, 'dev_advisories': 5,
            'exception': 'UNPATCHED_DEV_ONLY_BRACES_ADVISORY_NOT_A_PUBLIC_SITE_VULNERABILITY'}


def npm_audit(*args: str) -> dict:
    result = subprocess.run(['npm', 'audit', '--json', *args], cwd=WEB, capture_output=True, text=True)
    try:
        body = json.loads(result.stdout)
    except json.JSONDecodeError as err:
        raise RuntimeError('npm audit failed without parseable JSON') from err
    if result.returncode not in (0, 1) or body.get('error'):
        raise RuntimeError('npm audit registry or dependency inspection failed')
    return body


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--production-json', type=Path, help='Use fixture instead of registry audit (tests only)')
    parser.add_argument('--full-json', type=Path, help='Use fixture instead of registry audit (tests only)')
    args = parser.parse_args()
    if bool(args.production_json) != bool(args.full_json):
        parser.error('Both fixture paths required together')
    try:
        production = (json.loads(args.production_json.read_text()) if args.production_json
                      else npm_audit('--omit=dev'))
        full = json.loads(args.full_json.read_text()) if args.full_json else npm_audit()
        print('MUSBREAD_NPM_AUDIT '+json.dumps({'status': 'PASS', **validate(production, full)}))
        return 0
    except Exception as err:
        print('MUSBREAD_NPM_AUDIT '+json.dumps({'status':'FAIL', 'error':str(err)[:350]}),file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
