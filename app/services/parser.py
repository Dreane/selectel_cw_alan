import logging
from typing import List

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.crud.vacancy import upsert_external_vacancies
from app.schemas.external import ExternalVacanciesResponse

logger = logging.getLogger(__name__)

API_URL = "https://api.selectel.ru/proxy/public/employee/api/public/vacancies"


async def fetch_page(client: httpx.AsyncClient, page: int) -> ExternalVacanciesResponse:
    response = await client.get(
        API_URL,
        params={"per_page": 1000, "page": page},
    )
    response.raise_for_status()
    return ExternalVacanciesResponse.model_validate(response.json())


async def parse_and_store(session: AsyncSession) -> int:
    logger.info("Старт парсинга вакансий")
    created_total = 0

    timeout = httpx.Timeout(10.0, read=20.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            page = 1
            while True:
                payload = await fetch_page(client, page)
                parsed_payloads = []
                for item in payload.items:
                    parsed_payloads.append(
                        {
                            "external_id": item.id,
                            "title": item.title,
                            "timetable_mode_name": item.timetable_mode.name,
                            "tag_name": item.tag.name,
                            "city_name": item.city.name.strip() if item.city else None,
                            "published_at": item.published_at,
                            "is_remote_available": item.is_remote_available,
                            "is_hot": item.is_hot,
                        }
                    )

                created_count = await upsert_external_vacancies(session, parsed_payloads)
                created_total += created_count

                if page >= payload.page_count:
                    break
                page += 1
    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        logger.exception("Ошибка парсинга вакансий: %s", exc)
        return 0

    logger.info("Парсинг завершен, новых вакансий: %s", created_total)
    return created_total
