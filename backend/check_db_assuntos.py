import asyncio
import sys
from sqlalchemy import text
from app.db.engine import AsyncSessionLocal, close_db

async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
            SELECT column_name, data_type, character_maximum_length 
            FROM information_schema.columns 
            WHERE table_name = 'tpu_assuntos';
        """))
        for row in result:
            print(row)
    await close_db()

if __name__ == "__main__":
    asyncio.run(main())
