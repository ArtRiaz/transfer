from sqlalchemy import select, delete, update, func, false
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
            referral_id: Optional[str] = None,
            private_key: Optional[str] = None,
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
                referral_id=referral_id,
                refer=0,  # Новый пользователь еще никого не пригласил
                private_key_encrypted=private_key,
                transactions=False,
                amount_tx=0,
                referral_bonus=0,
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

    async def count_users(self) -> list[tuple[int, str]]:
        """
        Возвращает список всех пользователей (их ID и username).
        """
        query = select(User.user_id, User.username)
        result = await self.session.execute(query)
        return [(row.user_id, row.username) for row in result.fetchall()]

    async def save_wallet(self, user_id: int, encrypted_private_key: str):
        """Сохраняет Solana-адрес и зашифрованный приватный ключ в базу данных."""
        update_stmt = (
            update(User)
            .where(User.user_id == user_id)
            .values(
                private_key_encrypted=encrypted_private_key
            )
        )
        await self.session.execute(update_stmt)
        await self.session.commit()

    async def update_transaction_data(self, user_id: int, amount: int):
        """
        Обновляет статус `transactions` в True и увеличивает `amount_tx` на сумму новой транзакции.
        """
        update_stmt = (
            update(User)
            .where(User.user_id == user_id)
            .values(
                transactions=True,
                amount_tx=User.amount_tx + amount  # Увеличиваем сумму транзакций
            )
        )
        await self.session.execute(update_stmt)
        await self.session.commit()

    async def update_referral_bonus(self, user_id: int, amount: int):
        """
        Засчитываем реферала (только за первую транзакцию) и начисляем 8% бонуса.
        """
        # ✅ Получаем ID реферера и статус транзакций пользователя
        query = select(User.referral_id, User.transactions).where(User.user_id == user_id)
        result = await self.session.execute(query)
        referral_data = result.first()

        if not referral_data or not referral_data.referral_id:
            return  # ❌ Если реферера нет, выходим

        referral_id = referral_data.referral_id
        user_had_transactions = referral_data.transactions  # Было ли у пользователя раньше успешных транзакций

        # ✅ Начисляем бонус только если это первая транзакция реферала
        if not user_had_transactions:
            # referral_bonus = int(amount * 0.08)  # 8% бонуса
            referral_count_query = select(func.count()).where(User.referral_id == referral_id)
            referral_count_result = await self.session.execute(referral_count_query)
            referral_count = referral_count_result.scalar() or 0

            # Определяем процент бонуса
            bonus_percentage = 0.15 if referral_count > 10 else 0.08
            referral_bonus = int(amount * bonus_percentage)

            # ✅ Обновляем `referral_bonus`
            bonus_update_stmt = (
                update(User)
                .where(User.user_id == referral_id)
                .values(referral_bonus=User.referral_bonus + referral_bonus)
            )
            await self.session.execute(bonus_update_stmt)

            await self.session.commit()

    async def get_all_users(self) -> list[User]:
        """
        Получает список всех пользователей в базе.
        """
        query = select(User)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def claim_referral_bonus(self, user_id: int) -> int:
        """
        Позволяет пользователю получить (списать) реферальный бонус.
        Если бонус есть, он обнуляется, а функция возвращает списанную сумму.
        """
        # ✅ Получаем текущий бонус пользователя
        query = select(User.referral_bonus).where(User.user_id == user_id)
        result = await self.session.execute(query)
        referral_bonus = result.scalar_one_or_none()  # ❌ Исправлено: используем scalar_one_or_none()

        if referral_bonus is None:
            return 0  # ❌ Если пользователь не найден, нечего списывать

        if referral_bonus == 0:
            return 0  # ❌ Если бонус уже обнулен, выходим

        # ✅ Обнуляем бонус
        update_stmt = (
            update(User)
            .where(User.user_id == user_id)
            .values(referral_bonus=0)
            .returning(User.referral_bonus)
        )

        await self.session.execute(update_stmt)
        await self.session.commit()
        return referral_bonus  # ✅ Возвращаем сумму списанного бонуса

