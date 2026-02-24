#!/usr/bin/env python3
"""
Backup database before deletion operations.
"""

import sqlite3
import shutil
import os
from datetime import datetime

# Paths
db_path = r"C:\Users\joengzaang\PycharmProjects\villages-ML\data\villages.db"
backup_dir = r"C:\Users\joengzaang\PycharmProjects\villages-ML\data\backups"
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_path = os.path.join(backup_dir, f"villages_backup_{timestamp}.db")

# Create backup directory if it doesn't exist
os.makedirs(backup_dir, exist_ok=True)

print(f"Creating backup of database...")
print(f"Source: {db_path}")
print(f"Destination: {backup_path}")

# Get original size
original_size = os.path.getsize(db_path) / (1024 * 1024 * 1024)  # GB
print(f"Original size: {original_size:.2f} GB")

# Create backup
shutil.copy2(db_path, backup_path)

# Verify backup
backup_size = os.path.getsize(backup_path) / (1024 * 1024 * 1024)  # GB
print(f"Backup size: {backup_size:.2f} GB")

if abs(original_size - backup_size) < 0.01:  # Within 10MB
    print("\n[+] Backup created successfully!")
    print(f"\nBackup location: {backup_path}")
else:
    print("\n[-] Backup size mismatch! Please verify manually.")
    exit(1)

# Test backup integrity
try:
    conn = sqlite3.connect(backup_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM 广东省自然村")
    count = cursor.fetchone()[0]
    conn.close()
    print(f"[+] Backup integrity verified: {count:,} villages")
except Exception as e:
    print(f"\n[-] Backup integrity check failed: {e}")
    exit(1)
