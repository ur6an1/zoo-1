"""Модели базы данных."""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Pet(Base):
    """Профиль питомца."""

    __tablename__ = "pets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    name: Mapped[str] = mapped_column(String(100))
    species: Mapped[str] = mapped_column(String(50))
    breed: Mapped[str] = mapped_column(String(100), default="")
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    photo_file_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    reminders: Mapped[list["Reminder"]] = relationship(back_populates="pet", cascade="all, delete-orphan")
    vaccinations: Mapped[list["Vaccination"]] = relationship(back_populates="pet", cascade="all, delete-orphan")
    vet_visits: Mapped[list["VetVisit"]] = relationship(back_populates="pet", cascade="all, delete-orphan")
    weight_records: Mapped[list["WeightRecord"]] = relationship(back_populates="pet", cascade="all, delete-orphan")
    food_entries: Mapped[list["FoodEntry"]] = relationship(back_populates="pet", cascade="all, delete-orphan")
    water_entries: Mapped[list["WaterEntry"]] = relationship(back_populates="pet", cascade="all, delete-orphan")
    allergies: Mapped[list["Allergy"]] = relationship(back_populates="pet", cascade="all, delete-orphan")
    documents: Mapped[list["Document"]] = relationship(back_populates="pet", cascade="all, delete-orphan")
    voice_notes: Mapped[list["VoiceNote"]] = relationship(back_populates="pet", cascade="all, delete-orphan")

    def age_str(self) -> str:
        if not self.birth_date:
            return "не указан"
        today = date.today()
        years = today.year - self.birth_date.year
        months = today.month - self.birth_date.month
        if months < 0:
            years -= 1
            months += 12
        if years > 0:
            y_word = "год" if years % 10 == 1 and years != 11 else "лет"
            if years % 10 in (2, 3, 4) and years not in (12, 13, 14):
                y_word = "года"
            return f"{years} {y_word}"
        if months > 0:
            return f"{months} мес."
        days = (today - self.birth_date).days
        return f"{days} дн."

    def age_months(self) -> int | None:
        if not self.birth_date:
            return None
        today = date.today()
        return (today.year - self.birth_date.year) * 12 + (today.month - self.birth_date.month)

    @property
    def species_emoji(self) -> str:
        emojis = {"кошка": "🐱", "собака": "🐶", "птица": "🐦", "грызун": "🐹"}
        return emojis.get(self.species, "🐾")


class UserSettings(Base):
    """Настройки пользователя и подписка."""

    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    city: Mapped[str] = mapped_column(String(200), default="")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    premium_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    plan_tier: Mapped[str] = mapped_column(String(20), default="free")
    ai_requests_today: Mapped[int] = mapped_column(Integer, default=0)
    last_request_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    weather_notify: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProcessedPayment(Base):
    """Идемпотентность платежей: чтобы не начислять подписку повторно."""

    __tablename__ = "processed_payments"
    __table_args__ = (
        UniqueConstraint("provider", "payment_id", name="uq_processed_payments_provider_payment"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(20), index=True)
    payment_id: Mapped[str] = mapped_column(String(200), index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    plan_key: Mapped[str] = mapped_column(String(20), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PendingPayment(Base):
    """Платежи, ожидающие автоматического подтверждения."""

    __tablename__ = "pending_payments"
    __table_args__ = (
        UniqueConstraint("provider", "payment_id", name="uq_pending_payments_provider_payment"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(20), index=True)
    payment_id: Mapped[str] = mapped_column(String(200), index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    plan_key: Mapped[str] = mapped_column(String(20), default="")
    amount_value: Mapped[str] = mapped_column(String(20), default="")
    currency: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(40), default="pending", index=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AnalyticsEvent(Base):
    """Минимальная продуктовая аналитика по воронке."""

    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    event_name: Mapped[str] = mapped_column(String(100), index=True)
    source: Mapped[str] = mapped_column(String(100), default="", index=True)
    payload_json: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class VoiceNote(Base):
    """Голосовая заметка."""

    __tablename__ = "voice_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    file_id: Mapped[str] = mapped_column(String(200))
    transcription: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    pet: Mapped["Pet"] = relationship(back_populates="voice_notes")


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    category: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    remind_at: Mapped[datetime] = mapped_column(DateTime)
    repeat: Mapped[str] = mapped_column(String(20), default="once")
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    pet: Mapped["Pet"] = relationship(back_populates="reminders")

    @property
    def category_emoji(self) -> str:
        emojis = {"feeding": "🍽", "vaccine": "💉", "vet": "🏥", "grooming": "✂️", "custom": "📌"}
        return emojis.get(self.category, "⏰")

    @property
    def repeat_text(self) -> str:
        texts = {
            "once": "разово", "daily": "ежедневно", "weekly": "еженедельно",
            "monthly": "ежемесячно", "yearly": "ежегодно",
        }
        return texts.get(self.repeat, self.repeat)


class Vaccination(Base):
    __tablename__ = "vaccinations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200))
    date_done: Mapped[date] = mapped_column(Date)
    next_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    pet: Mapped["Pet"] = relationship(back_populates="vaccinations")


class VetVisit(Base):
    __tablename__ = "vet_visits"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="CASCADE"))
    visit_date: Mapped[date] = mapped_column(Date)
    diagnosis: Mapped[str] = mapped_column(Text, default="")
    treatment: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    pet: Mapped["Pet"] = relationship(back_populates="vet_visits")


class WeightRecord(Base):
    __tablename__ = "weight_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="CASCADE"))
    weight: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[date] = mapped_column(Date, default=date.today)
    pet: Mapped["Pet"] = relationship(back_populates="weight_records")


class FoodEntry(Base):
    __tablename__ = "food_entries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="CASCADE"))
    food_name: Mapped[str] = mapped_column(String(200))
    portion: Mapped[str] = mapped_column(String(100), default="")
    portion_grams: Mapped[float | None] = mapped_column(Float, nullable=True)
    meal_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[str] = mapped_column(Text, default="")
    pet: Mapped["Pet"] = relationship(back_populates="food_entries")


class WaterEntry(Base):
    __tablename__ = "water_entries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="CASCADE"))
    amount_ml: Mapped[int] = mapped_column(Integer)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    pet: Mapped["Pet"] = relationship(back_populates="water_entries")


class Allergy(Base):
    __tablename__ = "allergies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="CASCADE"))
    allergen: Mapped[str] = mapped_column(String(200))
    reaction: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    pet: Mapped["Pet"] = relationship(back_populates="allergies")


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="CASCADE"))
    doc_type: Mapped[str] = mapped_column(String(100))
    file_id: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    pet: Mapped["Pet"] = relationship(back_populates="documents")
