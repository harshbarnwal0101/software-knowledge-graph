"""
Parser registry — language detection and parser dispatch.
"""
from pathlib import Path
from typing import Optional, List

from app.parsers.base import BaseParser, ParsedFile
from app.parsers.python_parser import PythonParser
from app.parsers.javascript_parser import JavaScriptParser

# Files/dirs to skip during discovery
SKIP_DIRS = {
    ".git", ".hg", ".svn",
    "node_modules", "__pycache__", ".venv", "venv", "env",
    ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "dist", "build", ".next", "out",
    "vendor", "third_party",
}

SKIP_EXTENSIONS = {
    ".pyc", ".pyo", ".so", ".dylib", ".dll",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".eot",
    ".pdf", ".zip", ".tar", ".gz",
    ".lock", ".sum",
    ".min.js", ".min.css",
}

# Max file size to parse (2 MB)
MAX_FILE_SIZE = 2 * 1024 * 1024


class ParserRegistry:
    """
    Manages language parsers.
    Add new parsers here to extend language support.
    """

    def __init__(self):
        self._parsers: List[BaseParser] = [
            PythonParser(),
            JavaScriptParser(),
        ]
        self._ext_map: dict[str, BaseParser] = {}
        for parser in self._parsers:
            for ext in parser.extensions:
                self._ext_map[ext] = parser

    def get_parser(self, file_path: Path) -> Optional[BaseParser]:
        ext = file_path.suffix.lower()
        return self._ext_map.get(ext)

    def supported_extensions(self) -> List[str]:
        return list(self._ext_map.keys())

    def discover_files(self, repo_path: Path) -> List[Path]:
        """
        Walk repo directory and return all parseable source files,
        skipping binary files, generated files, and large files.
        """
        files = []
        for item in repo_path.rglob("*"):
            if not item.is_file():
                continue

            # Skip hidden dirs and known non-source dirs
            parts = set(item.parts)
            if any(part.startswith(".") or part in SKIP_DIRS for part in item.parts[len(repo_path.parts):]):
                continue

            # Skip by extension
            if item.suffix.lower() in SKIP_EXTENSIONS:
                continue
            if item.name.endswith(".min.js") or item.name.endswith(".min.css"):
                continue

            # Skip if no parser supports it
            if not self.get_parser(item):
                continue

            # Skip large files
            try:
                if item.stat().st_size > MAX_FILE_SIZE:
                    continue
            except OSError:
                continue

            files.append(item)

        return sorted(files)

    def parse_file(self, file_path: Path) -> Optional[ParsedFile]:
        parser = self.get_parser(file_path)
        if parser is None:
            return None
        return parser.parse_file(file_path)


# Singleton
registry = ParserRegistry()
