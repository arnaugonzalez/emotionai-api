#!/usr/bin/env python3
"""
Database Management Script for EmotionAI API

This script provides various database management utilities:
- Create/drop schema
- Run migrations
- Generate new migrations
- Show database status
- Backup/restore utilities
"""

import asyncio
import sys
import subprocess
import os
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.infrastructure.config.settings import settings

def run_command(command, description=None):
    """Run a shell command and handle errors"""
    if description:
        print(f"🔄 {description}...")
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        return False

def check_alembic():
    """Check if Alembic is installed and configured"""
    try:
        subprocess.run(["alembic", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Alembic not found. Please install: pip install alembic")
        return False

def init_migrations():
    """Initialize Alembic migrations"""
    print("🚀 Initializing database migrations...")
    
    if not check_alembic():
        return False
    
    # Check if migrations are already initialized
    if Path("migrations/env.py").exists():
        print("✅ Migrations already initialized")
        return True
    
    # Initialize Alembic
    if not run_command("alembic init migrations", "Initializing Alembic"):
        return False
    
    print("✅ Migrations initialized successfully")
    return True

def create_migration(message=None):
    """Create a new migration"""
    if not check_alembic():
        return False
    
    if not message:
        message = input("Enter migration message: ").strip()
        if not message:
            message = f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    command = f'alembic revision --autogenerate -m "{message}"'
    return run_command(command, f"Creating migration: {message}")

def run_migrations():
    """Run pending migrations"""
    if not check_alembic():
        return False
    
    return run_command("alembic upgrade head", "Running migrations")

def rollback_migration(steps=1):
    """Rollback migrations"""
    if not check_alembic():
        return False
    
    command = f"alembic downgrade -{steps}"
    return run_command(command, f"Rolling back {steps} migration(s)")

def show_migration_status():
    """Show current migration status"""
    if not check_alembic():
        return False
    
    print("📋 Migration Status:")
    print("-" * 50)
    
    # Show current revision
    run_command("alembic current", "Current revision")
    
    # Show migration history
    run_command("alembic history --verbose", "Migration history")

async def create_initial_schema():
    """Create the initial database schema without migrations"""
    from create_schema import create_database_schema
    await create_database_schema()

async def drop_schema():
    """Drop all database tables"""
    from create_schema import drop_schema
    await drop_schema()

async def show_schema_info():
    """Show database schema information"""
    from create_schema import show_schema_info
    await show_schema_info()

def backup_database():
    """Create a database backup"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"backup_emotionai_{timestamp}.sql"
    
    # Extract connection details from DATABASE_URL
    import re
    match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', settings.database_url)
    if not match:
        print("❌ Invalid database URL format")
        return False
    
    user, password, host, port, database = match.groups()
    
    command = f'PGPASSWORD="{password}" pg_dump -h {host} -p {port} -U {user} -d {database} > {backup_file}'
    
    if run_command(command, f"Creating backup: {backup_file}"):
        print(f"✅ Backup created: {backup_file}")
        return True
    return False

def restore_database(backup_file):
    """Restore database from backup"""
    if not Path(backup_file).exists():
        print(f"❌ Backup file not found: {backup_file}")
        return False
    
    # Extract connection details from DATABASE_URL
    import re
    match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', settings.database_url)
    if not match:
        print("❌ Invalid database URL format")
        return False
    
    user, password, host, port, database = match.groups()
    
    # First drop and recreate database
    print("⚠️  This will DROP and recreate the database!")
    response = input("Are you sure? Type 'yes' to confirm: ")
    if response.lower() != 'yes':
        print("❌ Operation cancelled")
        return False
    
    # Restore from backup
    command = f'PGPASSWORD="{password}" psql -h {host} -p {port} -U {user} -d {database} < {backup_file}'
    
    return run_command(command, f"Restoring from backup: {backup_file}")

def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database management for EmotionAI API")
    parser.add_argument("command", choices=[
        "init",           # Initialize migrations
        "create-schema",  # Create initial schema (no migrations)
        "drop-schema",    # Drop all tables
        "migrate",        # Run migrations
        "new-migration",  # Create new migration
        "rollback",       # Rollback migrations
        "status",         # Show migration status
        "info",           # Show database info
        "backup",         # Create backup
        "restore",        # Restore from backup
    ], help="Command to execute")
    
    parser.add_argument("--message", "-m", help="Migration message")
    parser.add_argument("--steps", type=int, default=1, help="Number of steps to rollback")
    parser.add_argument("--file", help="Backup file for restore")
    
    args = parser.parse_args()
    
    print("🏥 EmotionAI Database Manager")
    print("=" * 40)
    print(f"Environment: {settings.environment}")
    print(f"Database: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'Unknown'}")
    print()
    
    if args.command == "init":
        init_migrations()
        
    elif args.command == "create-schema":
        asyncio.run(create_initial_schema())
        
    elif args.command == "drop-schema":
        asyncio.run(drop_schema())
        
    elif args.command == "migrate":
        run_migrations()
        
    elif args.command == "new-migration":
        create_migration(args.message)
        
    elif args.command == "rollback":
        rollback_migration(args.steps)
        
    elif args.command == "status":
        show_migration_status()
        
    elif args.command == "info":
        asyncio.run(show_schema_info())
        
    elif args.command == "backup":
        backup_database()
        
    elif args.command == "restore":
        if not args.file:
            print("❌ --file parameter required for restore")
            return
        restore_database(args.file)

if __name__ == "__main__":
    main()