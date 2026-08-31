import asyncio
import logging
import sys

from app.core.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.repository import Repository
from app.services.ingestion_service import run_analysis

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

async def main():
    print("Step 1: Connecting to DB")
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Repository))
        repo = res.scalars().first()
        if not repo:
            print("No repository found in database!")
            return
        print(f"Testing analysis for repo: {repo.id}")
        repo_id = repo.id
        
    print("Step 2: Calling run_analysis")
    await run_analysis(repo_id)
    print("Done")

if __name__ == "__main__":
    print("Starting")
    asyncio.run(main())
