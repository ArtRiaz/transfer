from typing import Optional

from sqlalchemy import String
from sqlalchemy import text, BIGINT, Boolean, true, false
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, TableNameMixin


class User(Base, TimestampMixin, TableNameMixin):
    user_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=False)
    username: Mapped[Optional[str]] = mapped_column(String(128))
    full_name: Mapped[str] = mapped_column(String(128))
    active: Mapped[bool] = mapped_column(Boolean, server_default=true())
    language: Mapped[str] = mapped_column(String(10), server_default=text("'en'"))
    referral_id: Mapped[Optional[int]] = mapped_column(BIGINT, nullable=True)
    refer: Mapped[int] = mapped_column(BIGINT, nullable=False, server_default="0")
    private_key_encrypted: Mapped[str] = mapped_column(String(512), nullable=True)
    transactions: Mapped[bool] = mapped_column(Boolean)
    amount_tx: Mapped[int] = mapped_column(BIGINT, nullable=False, server_default="0")
    referral_bonus: Mapped[int] = mapped_column(BIGINT, nullable=False, server_default="0")

    def __repr__(self):
        return f"<User {self.user_id} {self.username} {self.full_name}>"
