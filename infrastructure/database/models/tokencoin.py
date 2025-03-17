from typing import Optional

from sqlalchemy import String
from sqlalchemy import text, BIGINT, Boolean, true, false, Float, Date, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, TableNameMixin
from datetime import date, datetime


class TokenRate(Base, TimestampMixin, TableNameMixin):
    date: Mapped[date] = mapped_column(Date, primary_key=True, server_default=text("CURRENT_DATE"))
    rate: Mapped[float] = mapped_column(Float, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=func.now(),  # Локальное значение по умолчанию
        onupdate=func.now()  # Автообновление
    )

    def __repr__(self):
        return f"<TokenRate {self.date} {self.rate}>"
