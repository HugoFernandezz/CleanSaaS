"""Project model for organizing cleaning jobs."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.dataset import Dataset


class Project(Base, TimestampMixin):
    """
    Modelo para proyectos de limpieza de datos.

    Un proyecto agrupa múltiples datasets y jobs de limpieza relacionados.
    """

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relaciones
    datasets: Mapped[list["Dataset"]] = relationship(
        "Dataset",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name='{self.name}')>"


