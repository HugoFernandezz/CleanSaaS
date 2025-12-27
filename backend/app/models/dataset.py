"""Dataset model for uploaded data files."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.cleaning_job import CleaningJob
    from app.models.project import Project


class DatasetStatus(str, Enum):
    """Estados posibles de un dataset."""

    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class Dataset(Base, TimestampMixin):
    """
    Modelo para datasets (archivos de datos subidos).

    Representa un archivo CSV/Parquet almacenado en S3/MinIO.
    """

    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_path_s3: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[DatasetStatus] = mapped_column(
        String(20),
        nullable=False,
        default=DatasetStatus.UPLOADING,
        index=True,
    )
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relaciones
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="datasets",
        lazy="selectin",
    )
    cleaning_jobs: Mapped[list["CleaningJob"]] = relationship(
        "CleaningJob",
        back_populates="dataset",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Dataset(id={self.id}, project_id={self.project_id}, status='{self.status}')>"


