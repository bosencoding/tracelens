#!/usr/bin/env python3
"""Cleanup duplicate fingerprints in reference_cameras table.

This script finds and removes duplicate fingerprint entries, keeping one entry
per unique fingerprint and updating matches to point to the kept entry.

Priority for keeping entries:
1. is_auto_added = 0 (manual entries preferred)
2. If all is_auto_added = 1, keep the smallest id (earliest created)

Usage:
    python tools/cleanup_duplicate_fingerprints.py [OPTIONS]

Options:
    --dry-run    Print plan without deleting
    --verbose    Print detailed information per group
    --db PATH    Database path (default: backend/data/tracelens.db)
"""

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def backup_database(db_path: Path) -> Path:
    """Create a backup of the database."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = db_path.parent / f"{db_path.name}.backup-{timestamp}"
    shutil.copy2(db_path, backup_path)
    return backup_path


def find_duplicate_groups(conn: sqlite3.Connection) -> list[dict]:
    """Find all duplicate fingerprint groups."""
    cursor = conn.execute("""
        SELECT fingerprint_hex, COUNT(*) as count
        FROM reference_cameras
        WHERE fingerprint_hex IS NOT NULL
        GROUP BY fingerprint_hex
        HAVING count > 1
        ORDER BY count DESC
    """)
    
    groups = []
    for row in cursor:
        fingerprint_hex = row[0]
        count = row[1]
        
        # Get all entries for this fingerprint
        entries_cursor = conn.execute("""
            SELECT id, make, model, is_auto_added, label
            FROM reference_cameras
            WHERE fingerprint_hex = ?
            ORDER BY is_auto_added ASC, id ASC
        """, (fingerprint_hex,))
        
        entries = []
        for entry_row in entries_cursor:
            entries.append({
                "id": entry_row[0],
                "make": entry_row[1],
                "model": entry_row[2],
                "is_auto_added": entry_row[3],
                "label": entry_row[4],
            })
        
        groups.append({
            "fingerprint_hex": fingerprint_hex,
            "count": count,
            "entries": entries,
            "keep": entries[0],  # First entry after sorting
            "delete": entries[1:],  # Rest to delete
        })
    
    return groups


def update_matches(conn: sqlite3.Connection, old_id: str, new_id: str) -> int:
    """Update matches table to point from old_id to new_id."""
    cursor = conn.execute("""
        UPDATE matches
        SET reference_id = ?
        WHERE reference_id = ?
    """, (new_id, old_id))
    return cursor.rowcount


def delete_entry(conn: sqlite3.Connection, entry_id: str) -> None:
    """Delete a reference camera entry."""
    conn.execute("DELETE FROM reference_cameras WHERE id = ?", (entry_id,))


def main():
    parser = argparse.ArgumentParser(
        description="Cleanup duplicate fingerprints in reference_cameras table"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan without deleting",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed information per group",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("backend/data/tracelens.db"),
        help="Database path (default: backend/data/tracelens.db)",
    )
    
    args = parser.parse_args()
    
    db_path = args.db
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Database: {db_path}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print()
    
    # Backup database if not dry run
    if not args.dry_run:
        backup_path = backup_database(db_path)
        print(f"✓ Backup created: {backup_path}")
        print()
    
    conn = sqlite3.connect(db_path)
    conn.execute("BEGIN TRANSACTION")
    
    try:
        # Find duplicate groups
        groups = find_duplicate_groups(conn)
        
        if not groups:
            print("✓ No duplicate fingerprints found")
            conn.close()
            return
        
        print(f"Found {len(groups)} duplicate fingerprint groups")
        print()
        
        total_deleted = 0
        total_matches_updated = 0
        
        for i, group in enumerate(groups, 1):
            fingerprint = group["fingerprint_hex"]
            keep = group["keep"]
            delete_list = group["delete"]
            
            if args.verbose:
                print(f"Group {i}: fingerprint {fingerprint[:16]}...")
                print(f"  Count: {group['count']} entries")
                print(f"  Keep: {keep['id']} ({keep['make']} {keep['model']}, auto={keep['is_auto_added']})")
                print(f"  Delete: {len(delete_list)} entries")
                for entry in delete_list:
                    print(f"    - {entry['id']} ({entry['make']} {entry['model']}, auto={entry['is_auto_added']})")
                print()
            
            if not args.dry_run:
                # Update matches pointing to deleted entries
                for entry in delete_list:
                    matches_updated = update_matches(conn, entry["id"], keep["id"])
                    total_matches_updated += matches_updated
                
                # Delete entries
                for entry in delete_list:
                    delete_entry(conn, entry["id"])
                    total_deleted += 1
        
        if args.dry_run:
            print("DRY RUN SUMMARY:")
            print(f"  Groups found: {len(groups)}")
            print(f"  Entries to delete: {sum(len(g['delete']) for g in groups)}")
            print(f"  Entries to keep: {len(groups)}")
            print()
            print("Run without --dry-run to execute cleanup")
        else:
            conn.commit()
            print("✓ Cleanup completed")
            print()
            print("SUMMARY:")
            print(f"  Groups processed: {len(groups)}")
            print(f"  Entries deleted: {total_deleted}")
            print(f"  Matches updated: {total_matches_updated}")
            
            # Verify no duplicates remain
            remaining = find_duplicate_groups(conn)
            if remaining:
                print(f"  ⚠ Warning: {len(remaining)} duplicate groups still exist")
            else:
                print(f"  ✓ No duplicate fingerprints remaining")
    
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}", file=sys.stderr)
        print("Transaction rolled back", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
