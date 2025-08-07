#!/usr/bin/env python3
"""
Database Schema Creation Script for EmotionAI API
Creates all tables and indexes in PostgreSQL RDS database
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.infrastructure.config.settings import settings
from src.infrastructure.database.connection import DatabaseConnection, Base
from src.infrastructure.database.models import (
    UserModel,
    ConversationModel, 
    MessageModel,
    EmotionalRecordModel,
    BreathingSessionModel,
    DomainEventModel,
    UserProfileModel,
    TagSemanticModel
)

async def create_database_schema():
    """Create all database tables and indexes"""
    
    print("ðŸš€ Starting database schema creation...")
    print(f"ðŸ“ Environment: {settings.environment}")
    print(f"ðŸ”— Database URL: {settings.database_url.replace(settings.database_url.split('://')[1].split('@')[0], '***:***')}")
    
    try:
        # Create database connection
        print("\nðŸ“¡ Connecting to database...")
        db = await DatabaseConnection.create(settings)
        
        # Create all tables
        print("ðŸ—ï¸  Creating database tables...")
        
        # Import all models to ensure they're registered with Base
        print("ðŸ“ Registered models:")
        for table_name in Base.metadata.tables.keys():
            print(f"   - {table_name}")
        
        # Create tables with SQLAlchemy
        Base.metadata.create_all(bind=db.engine)
        
        print("\nâœ… Database schema created successfully!")
        
        # Verify tables exist
        print("\nðŸ” Verifying tables...")
        async with db.get_session() as session:
            from sqlalchemy import text
            
            # Get list of tables
            result = session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """))
            
            tables = [row[0] for row in result.fetchall()]
            
            print("ðŸ“‹ Created tables:")
            for table in tables:
                print(f"   âœ“ {table}")
            
            # Get table counts
            print("\nðŸ“Š Table status:")
            for table in tables:
                count_result = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = count_result.scalar()
                print(f"   - {table}: {count} rows")
        
        await db.close()
        print("\nðŸŽ‰ Schema creation completed successfully!")
        
    except Exception as e:
        print(f"\nâŒ Error creating database schema: {e}")
        print(f"   Error type: {type(e).__name__}")
        
        # Provide helpful troubleshooting
        if "does not exist" in str(e).lower():
            print("\nðŸ’¡ Troubleshooting:")
            print("   - Check if the database 'emotionai_prod' exists in RDS")
            print("   - Verify the database URL is correct")
            print("   - Ensure the user has CREATE privileges")
        
        elif "connect" in str(e).lower():
            print("\nðŸ’¡ Troubleshooting:")
            print("   - Check if RDS instance is running and accessible")
            print("   - Verify security group allows connections from your IP/EC2")
            print("   - Check if the RDS endpoint is correct")
        
        raise

async def drop_schema():
    """Drop all tables (use with caution!)"""
    print("âš ï¸  DROPPING ALL TABLES...")
    
    response = input("Are you sure you want to drop all tables? Type 'yes' to confirm: ")
    if response.lower() != 'yes':
        print("âŒ Operation cancelled")
        return
    
    try:
        db = await DatabaseConnection.create(settings)
        
        print("ðŸ—‘ï¸  Dropping all tables...")
        Base.metadata.drop_all(bind=db.engine)
        
        await db.close()
        print("âœ… All tables dropped successfully!")
        
    except Exception as e:
        print(f"âŒ Error dropping tables: {e}")
        raise

async def show_schema_info():
    """Show current database schema information"""
    try:
        db = await DatabaseConnection.create(settings)
        
        print("ðŸ“‹ Database Schema Information")
        print("=" * 50)
        
        async with db.get_session() as session:
            from sqlalchemy import text
            
            # Get database info
            db_info = session.execute(text("SELECT version()")).scalar()
            print(f"ðŸ˜ PostgreSQL Version: {db_info}")
            
            # Get database size
            size_result = session.execute(text("""
                SELECT pg_size_pretty(pg_database_size(current_database()))
            """))
            db_size = size_result.scalar()
            print(f"ðŸ’¾ Database Size: {db_size}")
            
            # Get tables with row counts and sizes
            tables_info = session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    attname,
                    typename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                FROM pg_tables t
                JOIN pg_attribute a ON a.attrelid = t.tablename::regclass
                JOIN pg_type ty ON ty.oid = a.atttypid
                WHERE schemaname = 'public'
                AND a.attnum > 0
                ORDER BY tablename, attname;
            """))
            
            print(f"\nðŸ“Š Tables and Columns:")
            current_table = None
            for row in tables_info.fetchall():
                schema, table, column, col_type, size = row
                if table != current_table:
                    print(f"\n   ðŸ“‹ {table} ({size})")
                    current_table = table
                print(f"      - {column}: {col_type}")
            
            # Get indexes
            indexes_info = session.execute(text("""
                SELECT 
                    t.relname as table_name,
                    i.relname as index_name,
                    array_to_string(array_agg(a.attname), ', ') as column_names
                FROM pg_class t
                JOIN pg_index ix ON t.oid = ix.indrelid
                JOIN pg_class i ON i.oid = ix.indexrelid
                JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
                WHERE t.relkind = 'r'
                AND t.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
                GROUP BY t.relname, i.relname
                ORDER BY t.relname, i.relname;
            """))
            
            print(f"\nðŸ” Indexes:")
            for row in indexes_info.fetchall():
                table, index, columns = row
                print(f"   - {table}.{index}: {columns}")
        
        await db.close()
        
    except Exception as e:
        print(f"âŒ Error getting schema info: {e}")
        raise

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Database schema management")
    parser.add_argument("action", choices=["create", "drop", "info"], 
                       help="Action to perform")
    parser.add_argument("--force", action="store_true",
                       help="Force action without confirmation")
    
    args = parser.parse_args()
    
    if args.action == "create":
        asyncio.run(create_database_schema())
    elif args.action == "drop":
        asyncio.run(drop_schema())
    elif args.action == "info":
        asyncio.run(show_schema_info())
