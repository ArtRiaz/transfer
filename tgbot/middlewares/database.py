from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Update
from infrastructure.database.repo.requests import RequestsRepo

class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, session_pool):
        self.session_pool = session_pool

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        async with self.session_pool() as session:
            repo = RequestsRepo(session)
            event_from_user = data.get("event_from_user")

            # Проверяем, есть ли пользователь в базе
            user = await repo.users.is_user_exists(event_from_user.id)

            if user:
                # Если пользователь найден, получаем его данные
                data["user"] = await repo.users.get_user_by_id(event_from_user.id)
            else:
                # Если пользователя нет, передаем None
                data["user"] = None

            data["repo"] = repo

            result = await handler(event, data)
        return result

