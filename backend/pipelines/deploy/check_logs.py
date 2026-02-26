#!/usr/bin/env python3
"""
Check logs helper for deploy pipelines

Supports:
- Inspecting local log files under `backend/data` (tail / show last N lines)
- Attempting to fetch Cloud Run logs via `gcloud run services logs read` (if gcloud is installed)

Usage examples:
  python -m backend.pipelines.deploy.check_logs --local --lines 200
  python -m backend.pipelines.deploy.check_logs --cloud-run my-service --limit 200
"""
from pathlib import Path
import argparse
import subprocess
import sys


def tail_lines(path: Path, lines: int = 200):
    try:
        with path.open('rb') as f:
            # Read from end in chunks
            avg_line_size = 200
            to_read = lines * avg_line_size
            try:
                f.seek(-to_read, 2)
            except OSError:
                f.seek(0)
            data = f.read().decode('utf-8', errors='replace')
            all_lines = data.splitlines()
            return '\n'.join(all_lines[-lines:])
    except Exception as e:
        return f'ERROR reading {path}: {e}'


def find_local_logs(base: Path):
    if not base.exists():
        return []
    candidates = []
    for p in base.iterdir():
        if p.is_file() and (p.suffix == '.log' or 'log' in p.name.lower()):
            candidates.append(p)
    # also search one level deep
    for p in base.glob('*/*.log'):
        candidates.append(p)
    return sorted(set(candidates))


def fetch_cloud_run_logs(service: str, project: str = None, region: str = None, limit: int = 200):
    cmd = ['gcloud', 'run', 'services', 'logs', 'read', service, f'--limit={limit}']
    if project:
        cmd.append(f'--project={project}')
    if region:
        cmd.append(f'--region={region}')
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        out = res.stdout or res.stderr
        return out
    except FileNotFoundError:
        return 'gcloud not found in PATH; cannot fetch Cloud Run logs.'


def main():
    parser = argparse.ArgumentParser(description='Check logs for deploy troubleshooting')
    parser.add_argument('--local', action='store_true', help='Show local log files under backend/data')
    parser.add_argument('--lines', type=int, default=200, help='Number of lines to show from the end of each log')
    parser.add_argument('--cloud-run', dest='cloud_run', type=str, help='Cloud Run service name to fetch logs for')
    parser.add_argument('--project', type=str, help='GCP project for gcloud')
    parser.add_argument('--region', type=str, help='GCP region for gcloud')
    parser.add_argument('--limit', type=int, default=200, help='Limit lines when fetching cloud logs')

    args = parser.parse_args()

    base = Path(__file__).resolve().parents[3] / 'backend' / 'data'

    did_any = False

    if args.local:
        did_any = True
        logs = find_local_logs(base)
        if not logs:
            print(f'No local logs found in {base}')
        else:
            for p in logs:
                print('\n' + '=' * 80)
                print(f'FILE: {p}')
                print('-' * 80)
                print(tail_lines(p, lines=args.lines))

    if args.cloud_run:
        did_any = True
        print('\n' + '=' * 80)
        print(f'Cloud Run logs for service: {args.cloud_run}')
        print('-' * 80)
        out = fetch_cloud_run_logs(args.cloud_run, project=args.project, region=args.region, limit=args.limit)
        print(out)

    if not did_any:
        parser.print_help()


if __name__ == '__main__':
    main()
