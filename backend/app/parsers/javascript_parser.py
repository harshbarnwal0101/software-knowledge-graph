"""
JavaScript/TypeScript parser — uses Tree-sitter to extract AST from .js/.ts/.jsx/.tsx files.
"""
import logging
from pathlib import Path
from typing import List, Optional

from app.parsers.base import BaseParser, ParsedFile, ParsedSymbol

logger = logging.getLogger(__name__)


def _load_js_parser():
    try:
        from tree_sitter import Language, Parser
        import tree_sitter_javascript as tsjs
        lang = Language(tsjs.language())
        parser = Parser(lang)
        return parser, lang
    except Exception as e:
        logger.warning(f"tree-sitter-javascript not available: {e}")
        return None, None


def _load_ts_parser():
    try:
        from tree_sitter import Language, Parser
        import tree_sitter_typescript as tsts
        lang = Language(tsts.language_typescript())
        parser = Parser(lang)
        return parser, lang
    except Exception as e:
        logger.warning(f"tree-sitter-typescript not available: {e}")
        return None, None


class JavaScriptParser(BaseParser):
    """AST-aware parser for JavaScript/TypeScript files."""

    def __init__(self):
        self._js_parser, _ = _load_js_parser()
        self._ts_parser, _ = _load_ts_parser()

    @property
    def language(self) -> str:
        return "javascript"

    @property
    def extensions(self) -> List[str]:
        return [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"]

    def parse_file(self, file_path: Path) -> ParsedFile:
        ext = file_path.suffix.lower()
        lang_name = "typescript" if ext in (".ts", ".tsx") else "javascript"

        try:
            source = file_path.read_bytes()
            lines = source.decode("utf-8", errors="replace").splitlines()
        except Exception as e:
            return ParsedFile(path=str(file_path), language=lang_name, lines=0, errors=[str(e)])

        result = ParsedFile(path=str(file_path), language=lang_name, lines=len(lines))

        parser = self._ts_parser if lang_name == "typescript" else self._js_parser

        if parser is None:
            result.symbols = self._regex_parse(lines)
            return result

        try:
            tree = parser.parse(source)
            result.symbols = self._walk_tree(tree.root_node, source)
        except Exception as e:
            logger.warning(f"tree-sitter JS/TS parse failed for {file_path}: {e}")
            result.errors.append(str(e))
            result.symbols = self._regex_parse(lines)

        return result

    def _node_text(self, node, source: bytes) -> str:
        return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

    def _walk_tree(self, root, source: bytes) -> List[ParsedSymbol]:
        symbols = []
        self._visit(root, source, symbols, current_class=None)
        return symbols

    def _visit(self, node, source, symbols, current_class):
        ntype = node.type

        # Class declaration
        if ntype in ("class_declaration", "class_expression"):
            name = self._get_identifier(node, source)
            if name:
                symbols.append(ParsedSymbol(
                    symbol_type="class", name=name, qualified_name=name,
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1,
                ))
                for child in node.children:
                    self._visit(child, source, symbols, current_class=name)
            return

        # Function / arrow function / method
        if ntype in ("function_declaration", "function_expression"):
            name = self._get_identifier(node, source) or "<anonymous>"
            sym_type = "method" if current_class else "function"
            qualified = f"{current_class}.{name}" if current_class else name
            symbols.append(ParsedSymbol(
                symbol_type=sym_type, name=name, qualified_name=qualified,
                parent_name=current_class,
                line_start=node.start_point[0] + 1,
                line_end=node.end_point[0] + 1,
            ))

        if ntype == "method_definition":
            name = self._get_identifier(node, source)
            if name and current_class:
                symbols.append(ParsedSymbol(
                    symbol_type="method", name=name,
                    qualified_name=f"{current_class}.{name}",
                    parent_name=current_class,
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1,
                ))

        # Imports
        if ntype == "import_statement":
            text = self._node_text(node, source).strip()
            # Extract module name from: import X from 'module'
            parts = text.split("from")
            mod = parts[-1].strip().strip("'\"`;") if "from" in text else text.split()[-1].strip("'\"`;")
            symbols.append(ParsedSymbol(
                symbol_type="import", name=mod[:200],
                qualified_name=text[:500],
                line_start=node.start_point[0] + 1,
                line_end=node.end_point[0] + 1,
            ))

        for child in node.children:
            self._visit(child, source, symbols, current_class)

    def _get_identifier(self, node, source) -> Optional[str]:
        for child in node.children:
            if child.type in ("identifier", "property_identifier", "type_identifier"):
                return self._node_text(child, source)
        return None

    def _regex_parse(self, lines: list) -> List[ParsedSymbol]:
        """Regex fallback for JS/TS."""
        import re
        symbols = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # class Foo
            cm = re.match(r"^(?:export\s+)?(?:default\s+)?class\s+(\w+)", stripped)
            if cm:
                symbols.append(ParsedSymbol(
                    symbol_type="class", name=cm.group(1),
                    qualified_name=cm.group(1), line_start=i, line_end=i,
                ))

            # function foo() or const foo = () =>
            fm = re.match(r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)", stripped)
            if fm:
                symbols.append(ParsedSymbol(
                    symbol_type="function", name=fm.group(1),
                    qualified_name=fm.group(1), line_start=i, line_end=i,
                ))

            # const foo = () =>  or  const foo = function
            af = re.match(r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)\s*=>|function)", stripped)
            if af:
                symbols.append(ParsedSymbol(
                    symbol_type="function", name=af.group(1),
                    qualified_name=af.group(1), line_start=i, line_end=i,
                ))

            # import
            im = re.match(r"^import\s+.+from\s+['\"](.+)['\"]", stripped)
            if im:
                symbols.append(ParsedSymbol(
                    symbol_type="import", name=im.group(1),
                    qualified_name=stripped[:500], line_start=i, line_end=i,
                ))

        return symbols
