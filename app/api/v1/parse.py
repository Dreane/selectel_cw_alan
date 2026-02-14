from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.services.parser import parse_and_store

router = APIRouter(prefix="/parse", tags=["parser"])


async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session


@router.post("/")
async def parse_endpoint(session: AsyncSession = Depends(get_session)) -> dict:
    created_count = await parse_and_store(session)
    return {"created": created_count}
