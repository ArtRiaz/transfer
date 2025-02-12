from sqlalchemy import select, delete, update, func
from sqlalchemy.dialects.postgresql import insert
from infrastructure.database.models import User
from infrastructure.database.repo.base import BaseRepo
from typing import Optional


class UserRepo(BaseRepo):
    async def count_referrals(self, referral_id: int) -> int:
        """
        Подсчитывает количество пользователей, которые зарегистрировались по данному referral_id.
        """
        query = select(func.count()).where(User.referral_id == referral_id)
        result = await self.session.execute(query)
        return result.scalar_one() or 0

    async def increase_referral_count(self, referral_id: int):
        """
        Увеличивает счетчик `refer` для пользователя, который является реферером.
        """
        update_stmt = (
            update(User)
            .where(User.user_id == referral_id)
            .values(refer=User.refer + 1)  # Увеличиваем `refer`
            .returning(User)
        )
        result = await self.session.execute(update_stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def get_or_create_user(
            self,
            user_id: int,
            full_name: str,
            language: str,
            username: Optional[str] = None,
            email: Optional[str] = None,
            referral_id: Optional[str] = None,
    ):
        """
        Записывает нового пользователя, если его нет.
        Если пользователь уже есть, просто возвращает его без обновления данных.
        """
        # Сначала проверяем, есть ли пользователь в базе
        query = select(User).where(User.user_id == user_id)
        result = await self.session.execute(query)
        existing_user = result.scalar_one_or_none()

        # Если пользователь уже есть, возвращаем его (НЕ обновляем)
        if existing_user:
            return existing_user

        # Если пользователя нет, создаем новую запись
        insert_stmt = (
            insert(User)
            .values(
                user_id=user_id,
                username=username,
                full_name=full_name,
                language=language,
                email=email,
                referral_id=referral_id,
                refer=0  # Новый пользователь еще никого не пригласил
            )
            .returning(User)
        )

        result = await self.session.execute(insert_stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def is_email_exists(self, email: str) -> bool:
        """
        Проверяет, существует ли email в базе.
        """
        query = select(User).where(User.email == email)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def is_user_exists(self, user_id: int) -> bool:
        """
        Проверяет, зарегистрирован ли пользователь.
        """
        query = select(User).where(User.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def clear_users(self):
        """
        Удаляет всех пользователей из таблицы users.
        """
        delete_stmt = delete(User)
        await self.session.execute(delete_stmt)
        await self.session.commit()

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Получает пользователя по user_id.
        """
        query = select(User).where(User.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()  # Возвращает объект User или None

    async def update_user_email(self, user_id: int, new_email: str):
        """
        Обновляет email конкретного пользователя, если он существует.
        """
        update_stmt = (
            update(User)
            .where(User.user_id == user_id)
            .values(email=new_email)
            .returning(User)
        )

        result = await self.session.execute(update_stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

