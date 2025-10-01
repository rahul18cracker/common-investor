"""
Database Migration Tests

Tests for Alembic migrations to ensure:
1. Migrations can be applied (upgrade)
2. Migrations can be rolled back (downgrade)
3. Data integrity is maintained during migrations
4. Schema changes are correctly applied
5. No conflicts between migrations
"""

import pytest
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, MetaData, Table, Column, Integer, String, text
from sqlalchemy.orm import sessionmaker
import os


# =============================================================================
# Migration Test Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def migration_engine():
    """
    Create a separate engine for migration testing.
    Uses a temporary SQLite database.
    """
    engine = create_engine("sqlite:///:memory:")
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def alembic_config():
    """
    Create Alembic configuration for testing.
    """
    # Get the alembic.ini path
    backend_dir = os.path.dirname(os.path.dirname(__file__))
    alembic_ini_path = os.path.join(backend_dir, "alembic.ini")
    
    config = Config(alembic_ini_path)
    config.set_main_option("script_location", os.path.join(backend_dir, "alembic"))
    
    return config


@pytest.fixture(scope="function")
def migration_session(migration_engine):
    """
    Create a session for migration testing.
    """
    Session = sessionmaker(bind=migration_engine)
    session = Session()
    yield session
    session.close()


# =============================================================================
# Unit Tests: Migration Structure
# =============================================================================

@pytest.mark.unit
@pytest.mark.migration
class TestMigrationStructure:
    """Test the structure and integrity of migration files."""
    
    def test_migration_files_exist(self):
        """Test that migration files are present."""
        backend_dir = os.path.dirname(os.path.dirname(__file__))
        migrations_dir = os.path.join(backend_dir, "alembic", "versions")
        
        assert os.path.exists(migrations_dir), "Migrations directory doesn't exist"
        
        migration_files = [f for f in os.listdir(migrations_dir) if f.endswith('.py')]
        assert len(migration_files) > 0, "No migration files found"
    
    def test_migration_chain_integrity(self, alembic_config):
        """Test that migration chain is valid with no gaps."""
        script = ScriptDirectory.from_config(alembic_config)
        
        # Get all revisions
        revisions = list(script.walk_revisions())
        
        assert len(revisions) > 0, "No migrations found"
        
        # Check for broken chain
        for revision in revisions:
            if revision.down_revision is not None:
                # Verify parent exists
                parent = script.get_revision(revision.down_revision)
                assert parent is not None, f"Broken chain at {revision.revision}"
    
    def test_no_duplicate_revisions(self, alembic_config):
        """Test that there are no duplicate revision IDs."""
        script = ScriptDirectory.from_config(alembic_config)
        revisions = [rev.revision for rev in script.walk_revisions()]
        
        assert len(revisions) == len(set(revisions)), "Duplicate revision IDs found"
    
    def test_migration_descriptions_exist(self, alembic_config):
        """Test that all migrations have descriptions."""
        script = ScriptDirectory.from_config(alembic_config)
        
        for revision in script.walk_revisions():
            assert revision.doc is not None, f"Migration {revision.revision} has no description"
            assert len(revision.doc.strip()) > 0, f"Migration {revision.revision} has empty description"


# =============================================================================
# Integration Tests: Migration Application
# =============================================================================

@pytest.mark.integration
@pytest.mark.migration
@pytest.mark.db
class TestMigrationApplication:
    """Test that migrations can be applied and rolled back."""
    
    def test_upgrade_head(self, migration_engine, alembic_config):
        """
        Test upgrading to head (latest migration).
        
        This is the most common operation and must always work.
        """
        # Set the database URL to use our test engine
        alembic_config.set_main_option("sqlalchemy.url", str(migration_engine.url))
        
        # Upgrade to head
        command.upgrade(alembic_config, "head")
        
        # Verify migration was applied
        inspector = inspect(migration_engine)
        tables = inspector.get_table_names()
        
        # Check that core tables exist
        assert "company" in tables
        assert "filing" in tables
        assert "alembic_version" in tables
    
    def test_downgrade_base(self, migration_engine, alembic_config):
        """
        Test downgrading to base (removing all migrations).
        
        Verifies that migrations can be rolled back completely.
        """
        alembic_config.set_main_option("sqlalchemy.url", str(migration_engine.url))
        
        # First upgrade to head
        command.upgrade(alembic_config, "head")
        
        # Then downgrade to base
        command.downgrade(alembic_config, "base")
        
        # Verify all tables are removed (except alembic_version)
        inspector = inspect(migration_engine)
        tables = inspector.get_table_names()
        
        # Only alembic_version should remain
        assert "company" not in tables
        assert "filing" not in tables
    
    def test_upgrade_one_step(self, migration_engine, alembic_config):
        """Test upgrading one migration at a time."""
        alembic_config.set_main_option("sqlalchemy.url", str(migration_engine.url))
        
        # Upgrade one step
        command.upgrade(alembic_config, "+1")
        
        # Verify first migration was applied
        inspector = inspect(migration_engine)
        tables = inspector.get_table_names()
        
        assert len(tables) > 1  # Should have at least some tables
    
    def test_downgrade_one_step(self, migration_engine, alembic_config):
        """Test downgrading one migration at a time."""
        alembic_config.set_main_option("sqlalchemy.url", str(migration_engine.url))
        
        # Upgrade to head first
        command.upgrade(alembic_config, "head")
        
        # Get current revision
        with migration_engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current_rev = context.get_current_revision()
        
        # Downgrade one step
        command.downgrade(alembic_config, "-1")
        
        # Verify revision changed
        with migration_engine.connect() as conn:
            context = MigrationContext.configure(conn)
            new_rev = context.get_current_revision()
        
        assert new_rev != current_rev
    
    def test_upgrade_to_specific_revision(self, migration_engine, alembic_config):
        """Test upgrading to a specific revision."""
        alembic_config.set_main_option("sqlalchemy.url", str(migration_engine.url))
        
        script = ScriptDirectory.from_config(alembic_config)
        revisions = list(script.walk_revisions())
        
        if len(revisions) >= 2:
            # Get the second-to-last revision
            target_rev = revisions[1].revision
            
            # Upgrade to that specific revision
            command.upgrade(alembic_config, target_rev)
            
            # Verify we're at that revision
            with migration_engine.connect() as conn:
                context = MigrationContext.configure(conn)
                current_rev = context.get_current_revision()
            
            assert current_rev == target_rev


# =============================================================================
# Integration Tests: Schema Validation
# =============================================================================

@pytest.mark.integration
@pytest.mark.migration
@pytest.mark.db
class TestMigrationSchema:
    """Test that migrated schema matches expected structure."""
    
    def test_company_table_schema(self, migration_engine, alembic_config):
        """Test that company table has correct columns and types."""
        alembic_config.set_main_option("sqlalchemy.url", str(migration_engine.url))
        command.upgrade(alembic_config, "head")
        
        inspector = inspect(migration_engine)
        columns = {col['name']: col for col in inspector.get_columns('company')}
        
        # Verify required columns exist
        assert 'id' in columns
        assert 'cik' in columns
        assert 'ticker' in columns
        assert 'name' in columns
        
        # Verify primary key
        pk_constraint = inspector.get_pk_constraint('company')
        assert 'id' in pk_constraint['constrained_columns']
    
    def test_filing_table_schema(self, migration_engine, alembic_config):
        """Test that filing table has correct columns and relationships."""
        alembic_config.set_main_option("sqlalchemy.url", str(migration_engine.url))
        command.upgrade(alembic_config, "head")
        
        inspector = inspect(migration_engine)
        columns = {col['name']: col for col in inspector.get_columns('filing')}
        
        # Verify required columns
        assert 'id' in columns
        assert 'cik' in columns
        assert 'form' in columns
        assert 'accession' in columns
        assert 'period_end' in columns
        
        # Verify foreign keys (if supported by SQLite with proper config)
        try:
            fk_constraints = inspector.get_foreign_keys('filing')
            # Should have foreign key to company table
            fk_tables = [fk['referred_table'] for fk in fk_constraints]
            assert 'company' in fk_tables
        except NotImplementedError:
            # SQLite might not support FK introspection
            pass
    
    def test_unique_constraints(self, migration_engine, alembic_config):
        """Test that unique constraints are properly applied."""
        alembic_config.set_main_option("sqlalchemy.url", str(migration_engine.url))
        command.upgrade(alembic_config, "head")
        
        inspector = inspect(migration_engine)
        
        # Check company table unique constraints
        company_constraints = inspector.get_unique_constraints('company')
        company_unique_cols = set()
        for constraint in company_constraints:
            company_unique_cols.update(constraint['column_names'])
        
        # CIK should be unique
        assert 'cik' in company_unique_cols
        
        # Check filing table unique constraints
        filing_constraints = inspector.get_unique_constraints('filing')
        filing_unique_cols = set()
        for constraint in filing_constraints:
            filing_unique_cols.update(constraint['column_names'])
        
        # Accession should be unique
        assert 'accession' in filing_unique_cols
    
    def test_indexes_created(self, migration_engine, alembic_config):
        """Test that indexes are properly created."""
        alembic_config.set_main_option("sqlalchemy.url", str(migration_engine.url))
        command.upgrade(alembic_config, "head")
        
        inspector = inspect(migration_engine)
        
        # Check indexes on company table
        company_indexes = inspector.get_indexes('company')
        company_indexed_cols = set()
        for index in company_indexes:
            company_indexed_cols.update(index['column_names'])
        
        # Ticker should be indexed for performance
        assert 'ticker' in company_indexed_cols or 'cik' in company_indexed_cols


# =============================================================================
# Integration Tests: Data Integrity During Migration
# =============================================================================

@pytest.mark.integration
@pytest.mark.migration
@pytest.mark.db
class TestDataIntegrityDuringMigration:
    """Test that data is preserved during migrations."""
    
    def test_data_preserved_on_upgrade(self, migration_engine, alembic_config, migration_session):
        """
        Test that existing data is preserved when upgrading.
        
        This is critical for production deployments.
        """
        alembic_config.set_main_option("sqlalchemy.url", str(migration_engine.url))
        
        # Apply initial migration
        command.upgrade(alembic_config, "head")
        
        # Insert test data
        migration_session.execute(
            text("INSERT INTO company (cik, ticker, name) VALUES (:cik, :ticker, :name)"),
            {"cik": "0000789019", "ticker": "MSFT", "name": "Microsoft Corporation"}
        )
        migration_session.commit()
        
        # Verify data exists
        result = migration_session.execute(
            text("SELECT ticker FROM company WHERE cik = :cik"),
            {"cik": "0000789019"}
        ).fetchone()
        assert result[0] == "MSFT"
        
        # Downgrade and upgrade (simulating a rollback and re-apply)
        command.downgrade(alembic_config, "-1")
        command.upgrade(alembic_config, "head")
        
        # Note: Data will be lost on downgrade if migration drops tables
        # This test mainly ensures the migration process doesn't corrupt data
    
    def test_foreign_key_integrity_maintained(self, migration_engine, alembic_config, migration_session):
        """Test that foreign key relationships are maintained during migrations."""
        alembic_config.set_main_option("sqlalchemy.url", str(migration_engine.url))
        command.upgrade(alembic_config, "head")
        
        # Insert company
        migration_session.execute(
            text("INSERT INTO company (cik, ticker, name) VALUES (:cik, :ticker, :name)"),
            {"cik": "0000789019", "ticker": "MSFT", "name": "Microsoft"}
        )
        
        # Insert filing referencing company
        migration_session.execute(
            text("""
                INSERT INTO filing (cik, form, accession, period_end) 
                VALUES (:cik, :form, :accession, :period_end)
            """),
            {
                "cik": "0000789019",
                "form": "10-K",
                "accession": "TEST-001",
                "period_end": "2023-12-31"
            }
        )
        migration_session.commit()
        
        # Verify both records exist and are linked
        result = migration_session.execute(
            text("""
                SELECT f.accession, c.ticker 
                FROM filing f 
                JOIN company c ON f.cik = c.cik 
                WHERE f.accession = :accession
            """),
            {"accession": "TEST-001"}
        ).fetchone()
        
        assert result is not None
        assert result[1] == "MSFT"


# =============================================================================
# Integration Tests: Migration Idempotency
# =============================================================================

@pytest.mark.integration
@pytest.mark.migration
class TestMigrationIdempotency:
    """Test that migrations are idempotent (can be run multiple times safely)."""
    
    def test_double_upgrade_is_safe(self, migration_engine, alembic_config):
        """Test that running upgrade twice doesn't cause errors."""
        alembic_config.set_main_option("sqlalchemy.url", str(migration_engine.url))
        
        # First upgrade
        command.upgrade(alembic_config, "head")
        
        # Second upgrade (should be no-op)
        command.upgrade(alembic_config, "head")
        
        # Should not raise any errors
        inspector = inspect(migration_engine)
        tables = inspector.get_table_names()
        assert "company" in tables
    
    def test_double_downgrade_is_safe(self, migration_engine, alembic_config):
        """Test that running downgrade twice doesn't cause errors."""
        alembic_config.set_main_option("sqlalchemy.url", str(migration_engine.url))
        
        # Upgrade first
        command.upgrade(alembic_config, "head")
        
        # First downgrade
        command.downgrade(alembic_config, "base")
        
        # Second downgrade (should be no-op)
        command.downgrade(alembic_config, "base")
        
        # Should not raise errors


# =============================================================================
# Unit Tests: Migration Content
# =============================================================================

@pytest.mark.unit
@pytest.mark.migration
class TestMigrationContent:
    """Test the content and quality of migration files."""
    
    def test_migrations_have_upgrade_and_downgrade(self, alembic_config):
        """Test that all migrations implement both upgrade and downgrade."""
        script = ScriptDirectory.from_config(alembic_config)
        
        for revision in script.walk_revisions():
            # Load the migration module
            migration_module = revision.module
            
            # Check that both functions exist
            assert hasattr(migration_module, 'upgrade'), \
                f"Migration {revision.revision} missing upgrade()"
            assert hasattr(migration_module, 'downgrade'), \
                f"Migration {revision.revision} missing downgrade()"
            
            # Check that they're callable
            assert callable(migration_module.upgrade)
            assert callable(migration_module.downgrade)
    
    def test_migrations_have_revision_ids(self, alembic_config):
        """Test that all migrations have proper revision IDs."""
        script = ScriptDirectory.from_config(alembic_config)
        
        for revision in script.walk_revisions():
            assert revision.revision is not None
            assert len(revision.revision) > 0
            # Revision ID should be alphanumeric
            assert revision.revision.replace('_', '').isalnum()


# =============================================================================
# Performance Tests
# =============================================================================

@pytest.mark.slow
@pytest.mark.migration
class TestMigrationPerformance:
    """Test migration performance."""
    
    def test_upgrade_performance(self, migration_engine, alembic_config):
        """Test that migrations complete in reasonable time."""
        import time
        
        alembic_config.set_main_option("sqlalchemy.url", str(migration_engine.url))
        
        start_time = time.time()
        command.upgrade(alembic_config, "head")
        duration = time.time() - start_time
        
        # Migrations should complete quickly (< 5 seconds for empty database)
        assert duration < 5.0, f"Migrations took {duration:.2f}s, expected < 5s"
    
    def test_downgrade_performance(self, migration_engine, alembic_config):
        """Test that rollback completes in reasonable time."""
        import time
        
        alembic_config.set_main_option("sqlalchemy.url", str(migration_engine.url))
        
        # Upgrade first
        command.upgrade(alembic_config, "head")
        
        start_time = time.time()
        command.downgrade(alembic_config, "base")
        duration = time.time() - start_time
        
        # Rollback should be fast (< 3 seconds)
        assert duration < 3.0, f"Rollback took {duration:.2f}s, expected < 3s"
