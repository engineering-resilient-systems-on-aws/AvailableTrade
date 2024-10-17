from datetime import datetime
import enum
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy import ForeignKey
from sqlalchemy import String


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customer"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(250))
    last_name: Mapped[str] = mapped_column(String(250))
    created_on: Mapped[datetime]
    updated_on: Mapped[datetime]

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Symbol(Base):
    __tablename__ = "symbol"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(25), primary_key=True)
    open: Mapped[float]
    high: Mapped[float]
    low: Mapped[float]
    close: Mapped[float]
    volume: Mapped[int]
    created_on: Mapped[datetime]
    updated_on: Mapped[datetime]

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class TransactionType(str, enum.Enum):
    buy = "buy"
    sell = "sell"


class TradeState(str, enum.Enum):
    submitted = "submitted"
    pending = "pending"
    rejected = "rejected"
    filled = "filled"
    aborted = "aborted"


class Activity(Base):
    __tablename__ = "activity"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str] = mapped_column(String(250), unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.id"), name="customer_id")
    symbol_ticker: Mapped[int] = mapped_column(ForeignKey("symbol.id"), name="symbol_ticker")
    type: Mapped[TransactionType] = mapped_column(name="type")
    status: Mapped[TradeState] = mapped_column(name="status")
    current_price: Mapped[float]
    share_count: Mapped[float]

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
