"""Simple database connection test - Windows compatible"""
import sys
import os
import subprocess

print("Testing database connections...")

# Method 1: Use psql via subprocess
try:
    print("\n1. Testing psql via subprocess...")
    env = os.environ.copy()
    env['PGPASSWORD'] = 'dtlite_pass'
    
    result = subprocess.run(
        ['psql', '-h', 'localhost', '-U', 'dtlite_user', '-d', 'postgres', '-c', 'SELECT version()'],
        capture_output=True,
        text=True,
        env=env,
        timeout=5
    )
    if result.returncode == 0:
        print(f"   Connected! {result.stdout.strip()[:80]}")
        
        # Check/create dtlite database
        result2 = subprocess.run(
            ['psql', '-h', 'localhost', '-U', 'dtlite_user', '-d', 'postgres', '-c', "SELECT 1 FROM pg_database WHERE datname='dtlite'"],
            capture_output=True,
            text=True,
            env=env,
            timeout=5
        )
        if '1 row' not in result2.stdout:
            print("   Creating database 'dtlite'...")
            subprocess.run(
                ['psql', '-h', 'localhost', '-U', 'dtlite_user', '-d', 'postgres', '-c', 'CREATE DATABASE dtlite'],
                capture_output=True,
                text=True,
                env=env,
                timeout=5
            )
    else:
        print(f"   Error: {result.stderr.strip()[:100] if result.stderr else 'unknown'}")
except Exception as e:
    print(f"   psql error: {type(e).__name__}: {str(e)[:100]}")

# Method 2: Try with explicit charset
try:
    import asyncio
    import asyncpg
    
    async def test_asyncpg():
        try:
            conn = await asyncpg.connect(
                host='127.0.0.1',
                port=5432,
                user='dtlite_user',
                password='dtlite_pass',
                database='dtlite'
            )
            result = await conn.fetchval('SELECT 1')
            print(f"   asyncpg connected! Result: {result}")
            
            # Check tables
            tables = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            print(f"   Tables found: {[t['table_name'] for t in tables]}")
            
            await conn.close()
        except Exception as e:
            print(f"   asyncpg error: {type(e).__name__}: {str(e)[:100]}")
    
    asyncio.run(test_asyncpg())
except ImportError:
    print("\nasyncpg not available")
except Exception as e:
    print(f"asyncpg test error: {e}")

print("\nConnection tests complete.")
