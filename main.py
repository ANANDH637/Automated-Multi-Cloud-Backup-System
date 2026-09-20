#!/usr/bin/env python3
"""
Automated Multi-Cloud Backup System — CLI entry point.

Usage:
    python main.py --run-once                 Run a single backup pass now
    python main.py --schedule                  Run continuously on the configured interval
    python main.py --list                      List all backups across providers
    python main.py --restore FILE --to DIR     Restore a specific backup archive
    python main.py --config path/to.yaml ...   Use a custom config file
"""
import argparse
import json
import sys

from backup_system.config import Config
from backup_system.backup_manager import BackupManager
from backup_system.scheduler import run_scheduled


def main():
    parser = argparse.ArgumentParser(description="Automated Multi-Cloud Backup System")
    parser.add_argument("--config", default="config.yaml", help="Path to config YAML file")
    parser.add_argument("--run-once", action="store_true", help="Run a single backup pass")
    parser.add_argument("--schedule", action="store_true", help="Run backups on a recurring schedule")
    parser.add_argument("--list", action="store_true", help="List backups across all providers")
    parser.add_argument("--restore", metavar="FILE", help="Remote backup filename to restore")
    parser.add_argument("--to", metavar="DIR", default="restored", help="Destination directory for restore")
    parser.add_argument("--provider", help="Specific provider to restore from")
    args = parser.parse_args()

    config = Config(args.config)
    manager = BackupManager(config)

    if args.run_once:
        report = manager.run_backup()
        print(json.dumps(report, indent=2, default=str))
    elif args.schedule:
        interval = config.get("schedule", "interval_minutes", default=60)
        run_scheduled(manager, interval)
    elif args.list:
        print(json.dumps(manager.list_all_backups(), indent=2))
    elif args.restore:
        dest = manager.restore(args.restore, args.to, args.provider)
        print(f"Restored to: {dest}")
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
