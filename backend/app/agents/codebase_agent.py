"""
Codebase AI Agent — LangGraph agent designed specifically for software knowledge graphs.
Answers architectural, dependency, bug-finding, and codebase questions with clickable citations.
"""
import re
import logging
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.agents.tools import (
    tool_search_code,
    tool_get_symbol,
    tool_get_file,
    tool_traverse_graph,
    tool_get_git_history,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are CodeGraph AI, an expert software architecture agent.
Your job is to answer developer questions about the repository using evidence from code, AST symbols, knowledge graph relationships, and git history.

STRICT RULES:
1. Every answer based on repository evidence MUST contain exact source citations formatted as:
   Source: `path/to/file.py:L42`
2. Do not hallucinate classes, methods, or files not present in the repository context.
3. Be professional, direct, concise, and structured. Use Markdown headings and bullet points.
"""


class CodebaseAgent:
    def __init__(self):
        self._llm = None
        if settings.openai_api_key:
            try:
                from openai import OpenAI
                self._llm = OpenAI(
                    api_key=settings.openai_api_key,
                    base_url=settings.openai_base_url,
                )
            except Exception:
                self._llm = None

    async def answer_question(self, repo_id: str, question: str) -> Dict[str, Any]:
        """
        Main agent invocation method.
        1. Executes tools to gather context.
        2. Formulates answer with citations.
        """
        tools_executed = []
        context_blocks = []
        citations = []

        # Step 1: Tool — Search code & symbols
        tools_executed.append("search_code")
        search_hits = await tool_search_code(repo_id, question)

        for hit in search_hits:
            file_path = hit.get("file_path", "")
            line = hit.get("line_start", 1)
            content = hit.get("content", "")

            context_blocks.append(f"File: {file_path}:{line}\nContent:\n{content}\n---")
            if file_path:
                citations.append({
                    "file_path": file_path,
                    "line": line,
                    "label": f"{file_path}:{line}"
                })

        # Step 2: Tool — Check if query mentions a symbol for graph traversal
        words = re.findall(r"\b[A-Z]\w+\b", question)
        for w in words[:2]:
            tools_executed.append(f"traverse_graph({w})")
            graph_res = await tool_traverse_graph(repo_id, w)
            if graph_res.get("connections"):
                conn_text = ", ".join([f"{c['relationship']} -> {c['target_name']}" for c in graph_res["connections"]])
                context_blocks.append(f"Graph Traversal for {w}: {conn_text}")

        # Step 3: LLM Generation
        combined_context = "\n\n".join(context_blocks) if context_blocks else "No relevant code found."

        if self._llm:
            try:
                prompt_messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"Repository Context:\n{combined_context}\n\nQuestion: {question}"
                    }
                ]
                res = self._llm.chat.completions.create(
                    model=settings.llm_model,
                    messages=prompt_messages,
                    temperature=0.2,
                )
                answer_text = res.choices[0].message.content
            except Exception as e:
                logger.warning(f"LLM call failed: {e}")
                answer_text = self._fallback_answer(question, search_hits)
        else:
            answer_text = self._fallback_answer(question, search_hits)

        return {
            "question": question,
            "answer": answer_text,
            "tools_executed": tools_executed,
            "citations": citations[:5],
        }

    def _fallback_answer(self, question: str, search_hits: List[Dict[str, Any]]) -> str:
        """Deterministic fallback response when LLM API keys are not provided."""
        if not search_hits:
            return "No matching code symbols or files were found for this query in the repository knowledge graph."

        lines = [f"### Codebase Analysis for: '{question}'\n"]
        lines.append("Based on repository parsing and knowledge graph index:\n")

        for idx, hit in enumerate(search_hits[:3], 1):
            fp = hit.get("file_path")
            line = hit.get("line_start", 1)
            name = hit.get("name", "symbol")
            stype = hit.get("type", "code")

            lines.append(f"**{idx}. `{name}` ({stype})**")
            lines.append(f"Location: `{fp}:{line}`")
            lines.append(f"```text\n{hit.get('content', '')[:300]}\n```\n")

        lines.append("\nSource Citations:")
        for hit in search_hits[:3]:
            lines.append(f"- `{hit.get('file_path')}:{hit.get('line_start', 1)}`")

        return "\n".join(lines)


# Singleton
codebase_agent = CodebaseAgent()
