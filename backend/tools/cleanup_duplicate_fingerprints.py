#!/usr/bin/env python3
"""Cleanup duplicate fingerprints in reference_cameras table.

Finds all duplicate fingerprints, keeps one entry per fingerprint (preferring
manual entries over auto-added), and deletes the rest. Updates matches table
to point to kept entries.

Usage:
    uv run python -m tools.cleanup_duplicate_fingerprints --dry-run
    uv run python -m tools.cleanup_duplicate_fingerprints --verbose
    uv run python -m tools.cleanup_duplicate_fingerprints
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

from app import db
from app.config import settings


def backup_database() -> Path:
    """Create backup of database before cleanup."""
    db_path = settings().db_path
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = db_path.parent / f"tracelens.db.backup-{timestamp}"
    shutil.copy2(db_path, backup_path)
    return backup_path


def find_duplicates() -> list[dict]:
    """Find all duplicate fingerprints with their entries."""
    # Get fingerprints that appear more than once
    dup_fps = db.rows(
        """SELECT fingerprint_hex, COUNT(*) as count 
           FROM reference_cameras 
           GROUP BY fingerprint_hex 
           HAVING COUNT(*) > 1
           ORDER BY count DESC"""
    )
    
    result = []
    for row in dup_fps:
        fp = row["fingerprint_hex"]
        entries = db.rows(
            """SELECT id, label, make, model, is_auto_added, note
               FROM reference_cameras 
               WHERE fingerprint_hex = ?
               ORDER BY is_auto_added ASC, id ASC""",
            (fp,)
        )
        result.append({
            "fingerprint": fp,
            "count": row["count"],
            "entries": entries,
        })
    
    return result


def decide_keep(entries: list[dict]) -> tuple[dict, list[dict]]:
    """Decide which entry to keep and which to delete.
    
    Priority:
    1. is_auto_added = 0 (manual entries preferred)
    2. If all is_auto_added = 1, keep smallest id (earliest)
    """
    # Sort: manual first (is_auto_added=0), then by id ascending
    sorted_entries = sorted(entries, key=lambda e: (e["is_auto_added"], e["id"]))
    keep = sorted_entries[0]
    delete = sorted_entries[1:]
    return keep, delete


def update_matches(old_id: str, new_id: str) -> int:
    """Update matches table to point to new reference_id."""
    return db.execute(
        "UPDATE matches SET reference_id = ? WHERE reference_id = ?",
        (new_id, old_id)
    )


def cleanup(dry_run: bool = False, verbose: bool = False) -> dict:
    """Main cleanup logic."""
    duplicates = find_duplicates()
    
    if not duplicates:
        return {"groups": 0, "deleted": 0, "kept": 0, "matches_updated": 0}
    
    summary = {
        "groups": len(duplicates),
        "deleted": 0,
        "kept": 0,
        "matches_updated": 0,
        "details": [],
    }
    
    for dup in duplicates:
        keep, delete = decide_keep(dup["entries"])
        
        detail = {
            "fingerprint": dup["fingerprint"][:16] + "...",
            "count": dup["count"],
            "keep_id": keep["id"],
            "keep_label": keep["label"],
            "delete_ids": [e["id"] for e in delete],
        }
        summary["details"].append(detail)
        
        if verbose or dry_run:
            print(f"\nFingerprint: {dup['fingerprint'][:32]}... ({dup['count']} entries)")
            print(f"  KEEP: {keep['id']} - {keep['label']} (auto={keep['is_auto_added']})")
            for e in delete:
                print(f"  DELETE: {e['id']} - {e['label']} (auto={e['is_auto_added']})")
        
        if not dry_run:
            # Update matches pointing to deleted entries
            for entry in delete:
                updated = update_matches(entry["id"], keep["id"])
                summary["matches_updated"] += updated
                
                # Delete the entry
                db.execute("DELETE FROM reference_cameras WHERE id = ?", (entry["id"],))
                summary["deleted"] += 1
            
            summary["kept"] += 1
    
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print plan without deleting")
    parser.add_argument("--verbose", action="store_true", help="Print detailed info per group")
    args = parser.parse_args()
    
    # Find duplicates first
    duplicates = find_duplicates()
    if not duplicates:
        print("No duplicate fingerprints found. Database is clean.")
        return 0
    
    print(f"Found {len(duplicates)} fingerprint groups with duplicates:")
    total_dupes = sum(d["count"] for d in duplicates)
    print(f"  Total entries involved: {total_dupes}")
    print(f"  Entries to delete: {total_dupes - len(duplicates)}")
    
    if args.dry_run:
        print("\n=== DRY RUN MODE ===")
        cleanup(dry_run=True, verbose=args.verbose)
        print("\nNo changes made. Run without --dry-run to apply cleanup.")
        return 0
    
    # Backup before cleanup
    backup_path = backup_database()
    print(f"\nBackup created: {backup_path}")
    
    # Run cleanup
    print("\nCleaning up...")
    summary = cleanup(dry_run=False, verbose=args.verbose)
    
    print(f"\nCleanup complete:")
    print(f"  Groups processed: {summary['groups']}")
    print(f"  Entries kept: {summary['kept']}")
    print(f"  Entries deleted: {summary['deleted']}")
    print(f"  Matches updated: {summary['matches_updated']}")
    
    # Verify no duplicates remain
    remaining = find_duplicates()
    if remaining:
        print(f"\nWARNING: {len(remaining)} duplicate groups still remain!")
        return 1
    
    print("\nVerification passed: no duplicate fingerprints remain.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
