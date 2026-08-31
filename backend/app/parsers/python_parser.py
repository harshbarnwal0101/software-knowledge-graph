"""
Python parser — uses Tree-sitter to extract AST information from .py files.
"""
import logging
from pathlib import Path
from typing import List, Optional

from app.parsers.base import BaseParser, ParsedFile, ParsedSymbol

logger = logging.getLogger(__name__)


def _load_parser():
    """Lazy-load tree-sitter Python parser."""
    try:
        from tree_sitter import Language, Parser
        import tree_sitter_python as tspython
        lang = Language(tspython.language())
        parser = Parser(lang)
        return parser, lang
    except Exception as e:
        logger.warning(f"tree-sitter-python not available: {e}")
        return None, None


class PythonParser(BaseParser):
    """
    AST-aware parser for Python source files.
    Extracts: classes, functions, methods, imports, docstrings.
    """

    def __init__(self):
        self._parser, self._lang = _load_parser()

    @property
    def language(self) -> str:
        return "python"

    @property
    def extensions(self) -> List[str]:
        return [".py"]

    def parse_file(self, file_path: Path) -> ParsedFile:
        try:
            source = file_path.read_bytes()
            lines = source.decode("utf-8", errors="replace").splitlines()
        except Exception as e:
            return ParsedFile(path=str(file_path), language="python", lines=0, errors=[str(e)])

        result = ParsedFile(path=str(file_path), language="python", lines=len(lines))

        if self._parser is None:
            # Fallback: basic regex-based extraction
            result.symbols = self._regex_parse(lines)
            return result

        try:
            tree = self._parser.parse(source)
            result.symbols = self._walk_tree(tree.root_node, lines, source)
        except Exception as e:
            logger.warning(f"tree-sitter parse failed for {file_path}: {e}")
            result.errors.append(str(e))
            result.symbols = self._regex_parse(lines)

        return result

    # ── Tree-sitter walking ────────────────────────────────────

    def _walk_tree(self, root, lines: list, source: bytes) -> List[ParsedSymbol]:
        symbols = []
        self._visit_node(root, lines, source, symbols, current_class=None)
        return symbols

    def _visit_node(self, node, lines, source, symbols, current_class):
        if node.type == "class_definition":
            sym = self._extract_class(node, lines, source)
            if sym:
                symbols.append(sym)
                # Visit children with class context
                for child in node.children:
                    self._visit_node(child, lines, source, symbols, current_class=sym.name)
            return  # Don't double-visit children

        elif node.type == "function_definition":
            sym = self._extract_function(node, lines, source, current_class)
            if sym:
                symbols.append(sym)

        elif node.type in ("import_statement", "import_from_statement"):
            sym = self._extract_import(node, source)
            if sym:
                symbols.append(sym)

        for child in node.children:
            self._visit_node(child, lines, source, symbols, current_class)

    def _node_text(self, node, source: bytes) -> str:
        return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

    def _extract_class(self, node, lines, source) -> Optional[ParsedSymbol]:
        name = None
        for child in node.children:
            if child.type == "identifier":
                name = self._node_text(child, source)
                break
        if not name:
            return None

        docstring = self._extract_docstring(node, source)
        return ParsedSymbol(
            symbol_type="class",
            name=name,
            qualified_name=name,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
            docstring=docstring,
        )

    def _extract_function(self, node, lines, source, current_class) -> Optional[ParsedSymbol]:
        name = None
        params = []
        for child in node.children:
            if child.type == "identifier":
                name = self._node_text(child, source)
            elif child.type == "parameters":
                params_text = self._node_text(child, source)
        if not name:
            return None

        sym_type = "method" if current_class else "function"
        qualified = f"{current_class}.{name}" if current_class else name
        docstring = self._extract_docstring(node, source)
        sig = f"def {name}({self._node_text(node.child_by_field_name('parameters'), source)[1:-1] if node.child_by_field_name('parameters') else ''})"

        return ParsedSymbol(
            symbol_type=sym_type,
            name=name,
            qualified_name=qualified,
            parent_name=current_class,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
            docstring=docstring,
            signature=sig,
        )

    def _extract_import(self, node, source) -> Optional[ParsedSymbol]:
        text = self._node_text(node, source).strip()
        # Extract the main module name
        name = text.split()[1] if len(text.split()) > 1 else text
        return ParsedSymbol(
            symbol_type="import",
            name=name[:200],  # cap length
            qualified_name=text[:500],
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
        )

    def _extract_docstring(self, node, source) -> Optional[str]:
        """Extract the first string literal from a function/class body as docstring."""
        for child in node.children:
            if child.type == "block":
                for stmt in child.children:
                    if stmt.type == "expression_statement":
                        for sub in stmt.children:
                            if sub.type in ("string", "concatenated_string"):
                                raw = self._node_text(sub, source)
                                return raw.strip('"\' \n').replace('"""', "").strip()[:500]
        return None

    # ── Regex fallback ─────────────────────────────────────────

    def _regex_parse(self, lines: list) -> List[ParsedSymbol]:
        """Simple line-by-line fallback when tree-sitter is unavailable."""
        import re
        symbols = []
        current_class = None
        class_indent = 0

        for i, line in enumerate(lines, 1):
            stripped = line.lstrip()
            indent = len(line) - len(stripped)

            # Track class context
            cm = re.match(r"^class\s+(\w+)", stripped)
            if cm:
                current_class = cm.group(1)
                class_indent = indent
                symbols.append(ParsedSymbol(
                    symbol_type="class", name=current_class,
                    qualified_name=current_class, line_start=i, line_end=i,
                ))
                continue

            # Reset class context if we dedent past it
            if current_class and indent <= class_indent and stripped and not stripped.startswith("#"):
                current_class = None

            fm = re.match(r"^def\s+(\w+)\s*\(([^)]*)\)", stripped)
            if fm:
                name = fm.group(1)
                sig = f"def {name}({fm.group(2)})"
                sym_type = "method" if current_class else "function"
                qualified = f"{current_class}.{name}" if current_class else name
                symbols.append(ParsedSymbol(
                    symbol_type=sym_type, name=name, qualified_name=qualified,
                    parent_name=current_class, line_start=i, line_end=i, signature=sig,
                ))

            im = re.match(r"^(?:import|from)\s+(\S+)", stripped)
            if im:
                symbols.append(ParsedSymbol(
                    symbol_type="import", name=im.group(1),
                    qualified_name=stripped[:500], line_start=i, line_end=i,
                ))

        return symbols
