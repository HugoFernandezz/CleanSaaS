"""CleaningJob model for data cleaning operations."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.dataset import Dataset


class CleaningJobStatus(str, Enum):
    """Estados posibles de un job de limpieza."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CleaningJob(Base, TimestampMixin):
    """
    Modelo para jobs de limpieza de datos.

    Representa una operación de limpieza aplicada a un dataset,
    con reglas definidas en formato JSON.
    """

    __tablename__ = "cleaning_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rules_config_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[CleaningJobStatus] = mapped_column(
        String(20),
        nullable=False,
        default=CleaningJobStatus.PENDING,
        index=True,
    )
    output_path_s3: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Relaciones
    dataset: Mapped["Dataset"] = relationship(
        "Dataset",
        back_populates="cleaning_jobs",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<CleaningJob(id={self.id}, dataset_id={self.dataset_id}, status='{self.status}')>"


