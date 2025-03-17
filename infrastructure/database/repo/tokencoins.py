from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from infrastructure.database.models import TokenRate
from infrastructure.database.repo.base import BaseRepo
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from typing import Optional


class TokenCoinRepo(BaseRepo):

    async def get_rate(self) -> Optional[float]:
        """Получить курс токена за сегодня"""
        result = await self.session.execute(
            select(TokenRate.rate).filter(TokenRate.date == date.today())
        )
        rate = result.scalar()
        print(f"📌 get_rate(): {rate}")  # Логируем для проверки
        return rate  # Вернёт None, если нет данных

    async def set_rate(self, new_rate: float):
        """Обновить или установить курс токена на текущий день"""
        stmt = (
            insert(TokenRate)
            .values(
                date=date.today(),
                rate=new_rate,
                updated_at=func.now(),
                created_at=func.now()  # ✅ `created_at`, если запись создаётся впервые
            )
            .on_conflict_do_update(
                index_elements=["date"],
                set_={"rate": new_rate, "updated_at": func.now()}
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()

