from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, Uuid

from app.db.base import Base


class ProductStage(str, Enum):
    IDEA = "idea"
    BRAND = "brand"
    DESIGN = "design"
    CONTENT = "content"
    COMPLIANCE = "compliance"
    READY = "ready"


class ProductStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


PIPELINE_STAGE_ORDER = (
    ProductStage.IDEA.value,
    ProductStage.BRAND.value,
    ProductStage.DESIGN.value,
    ProductStage.CONTENT.value,
    ProductStage.COMPLIANCE.value,
    ProductStage.READY.value,
)


def is_valid_stage(stage: str) -> bool:
    return stage in PIPELINE_STAGE_ORDER


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    stage: Mapped[str] = mapped_column(String(32), default=ProductStage.IDEA.value, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=ProductStatus.PENDING.value, nullable=False)
    data: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    history: Mapped[list["ProductHistory"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductHistory.created_at",
    )


class ProductHistory(Base):
    __tablename__ = "product_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    from_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_stage: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    product: Mapped[Product] = relationship(back_populates="history")
