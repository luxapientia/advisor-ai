#!/usr/bin/env python3
"""
Database migration helper script.

This script provides convenient commands for managing database migrations.
"""

import subprocess
import sys
import os

def run_command(cmd):
    """Run a command and return the result."""
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}")
        print(f"Return code: {e.returncode}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False

def main():
    """Main function to handle migration commands."""
    if len(sys.argv) < 2:
        print("Usage: python migrate.py <command>")
        print("Commands:")
        print("  init     - Initialize Alembic (if not already done)")
        print("  create   - Create a new migration")
        print("  upgrade  - Apply all pending migrations")
        print("  downgrade - Rollback one migration")
        print("  current  - Show current migration status")
        print("  history  - Show migration history")
        return
    
    command = sys.argv[1]
    
    # Change to backend directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    if command == "init":
        print("Initializing Alembic...")
        run_command("alembic init alembic")
        
    elif command == "create":
        if len(sys.argv) < 3:
            print("Usage: python migrate.py create <message>")
            return
        message = sys.argv[2]
        print(f"Creating migration: {message}")
        run_command(f"alembic revision --autogenerate -m '{message}'")
        
    elif command == "upgrade":
        print("Applying migrations...")
        run_command("alembic upgrade head")
        
    elif command == "downgrade":
        print("Rolling back one migration...")
        run_command("alembic downgrade -1")
        
    elif command == "current":
        print("Current migration status:")
        run_command("alembic current")
        
    elif command == "history":
        print("Migration history:")
        run_command("alembic history")
        
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()