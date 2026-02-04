#!/usr/bin/env python
"""
Database reset script using SQLAlchemy.
Safely drops and recreates all tables from ORM models.
"""

import sys
from sqlalchemy import create_engine, text, inspect
from app.core.config import settings
from app.db.models import Base


def reset_database():
    """Reset database: drop all tables and recreate from models."""
    
    print("🔄 Database Reset Script")
    print("-" * 50)
    
    # Create engine
    engine = create_engine(settings.database_url, echo=False)
    
    try:
        # Check if we can connect
        with engine.connect() as conn:
            print("✓ Connected to database")
            
            # Get list of tables before dropping
            inspector = inspect(engine)
            existing_tables = inspector.get_table_names()
            
            if existing_tables:
                print(f"✓ Found {len(existing_tables)} existing tables: {existing_tables}")
                
                # Drop all tables
                print("\n⚠️  Dropping all existing tables...")
                Base.metadata.drop_all(bind=engine)
                print("✓ All tables dropped")
            else:
                print("✓ No existing tables found")
        
        # Create pgvector extension
        print("\n🔧 Setting up extensions...")
        with engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            print("✓ pgvector extension created/verified")
        
        # Create all tables from models
        print("\n📋 Creating tables from ORM models...")
        Base.metadata.create_all(bind=engine)
        print("✓ All tables created successfully")
        
        # Verify tables were created
        with engine.connect() as conn:
            inspector = inspect(engine)
            new_tables = inspector.get_table_names()
            print(f"\n✓ Created {len(new_tables)} tables:")
            for table in sorted(new_tables):
                print(f"  - {table}")
        
        print("\n✅ Database reset complete!")
        print("-" * 50)
        print("\nNext steps:")
        print("1. Start the application: python -m uvicorn app.main:app --reload")
        print("2. Create a thread: POST /threads/")
        print("3. Register a model: POST /threads/models")
        print("4. Send messages and summaries will auto-generate after 4 messages")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("-" * 50)
        return False
    finally:
        engine.dispose()


if __name__ == "__main__":
    success = reset_database()
    sys.exit(0 if success else 1)
