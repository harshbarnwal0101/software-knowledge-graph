import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Symbol(Base):
    """
    Represents a code entity extracted from AST parsing:
    class, function, method, import, etc.
    """
    __tablename__ = "symbols"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_id: Mapped[str] = mapped_column(String, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(String, ForeignKey("file_records.id", ondelete="CASCADE"), nullable=True, index=True)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    language: Mapped[str] = mapped_column(String, nullable=True)

    # Symbol identity
    symbol_type: Mapped[str] = mapped_column(String, nullable=False)  # class | function | method | import | variable
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    qualified_name: Mapped[str] = mapped_column(String, nullable=True)  # e.g. UserService.create_user
    parent_name: Mapped[str] = mapped_column(String, nullable=True)   # parent class name for methods

    # Location
    line_start: Mapped[int] = mapped_column(Integer, default=0)
    line_end: Mapped[int] = mapped_column(Integer, default=0)

    # Extras
    docstring: Mapped[str] = mapped_column(String, nullable=True)
    signature: Mapped[str] = mapped_column(String, nullable=True)  # function signature

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Symbol {self.symbol_type}:{self.name}>"
