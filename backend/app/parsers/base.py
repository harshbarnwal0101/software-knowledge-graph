"""
Base parser — abstract interface all language parsers must implement.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class ParsedSymbol:
    """A single code entity extracted from AST parsing."""
    symbol_type: str          # class | function | method | import | variable
    name: str
    line_start: int
    line_end: int
    parent_name: Optional[str] = None    # class name for methods
    qualified_name: Optional[str] = None
    docstring: Optional[str] = None
    signature: Optional[str] = None


@dataclass
class ParsedFile:
    """Result of parsing one source file."""
    path: str
    language: str
    lines: int
    symbols: List[ParsedSymbol] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def classes(self) -> List[ParsedSymbol]:
        return [s for s in self.symbols if s.symbol_type == "class"]

    @property
    def functions(self) -> List[ParsedSymbol]:
        return [s for s in self.symbols if s.symbol_type == "function"]

    @property
    def methods(self) -> List[ParsedSymbol]:
        return [s for s in self.symbols if s.symbol_type == "method"]

    @property
    def imports(self) -> List[ParsedSymbol]:
        return [s for s in self.symbols if s.symbol_type == "import"]


class BaseParser(ABC):
    """All language parsers extend this."""

    @property
    @abstractmethod
    def language(self) -> str:
        """Return the language name e.g. 'python'"""

    @property
    @abstractmethod
    def extensions(self) -> List[str]:
        """Return supported file extensions e.g. ['.py']"""

    @abstractmethod
    def parse_file(self, file_path: Path) -> ParsedFile:
        """Parse a single source file and return extracted symbols."""

    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.extensions
