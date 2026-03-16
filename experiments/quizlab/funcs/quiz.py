"""Quiz lab — list, serve (stripped), and grade quizzes from markdown files."""

from __future__ import annotations

import math
import re
from pathlib import Path

from leap import nolog, noregcheck

# ── Helpers ──

_QUESTION_RE = re.compile(r"^##\s+Question\s+\d+\s*:\s*(\S+)", re.MULTILINE)
_RADIO_RE = re.compile(r"^- \(([x ])\)\s+(.*)$")
_CHECK_RE = re.compile(r"^- \[([x ])\]\s+(.*)$")
_NUMERIC_RE = re.compile(r"^=\s+(.+)$")


def _quiz_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "ui" / "quiz"


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split YAML frontmatter from body. Returns (frontmatter_dict, body)."""
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            import yaml
            fm = yaml.safe_load(text[3:end]) or {}
            body = text[end + 3:].strip()
            return fm, body
    return {}, text.strip()


def _parse_question(section: str) -> dict:
    """Parse a single question section into structured data.

    Returns dict with keys: type, choices, correct, explanation.
    - type: "radio", "checkbox", or "numeric"
    - choices: list of choice label strings (radio/checkbox) or None (numeric)
    - correct: int index (radio), list[int] indices (checkbox), or float (numeric)
    - explanation: str or None
    """
    lines = section.strip().split("\n")
    choices = []
    correct = None
    qtype = None
    explanation_lines = []
    in_explanation = False

    for line in lines:
        stripped = line.strip()

        # Blockquote explanation (after choices)
        if in_explanation:
            if stripped.startswith(">"):
                explanation_lines.append(stripped[1:].strip())
            else:
                explanation_lines.append(stripped)
            continue

        # Radio choice
        m = _RADIO_RE.match(stripped)
        if m:
            qtype = "radio"
            marker, label = m.group(1), m.group(2)
            if marker == "x":
                correct = len(choices)
            choices.append(label)
            continue

        # Checkbox choice
        m = _CHECK_RE.match(stripped)
        if m:
            if qtype is None:
                qtype = "checkbox"
                correct = []
            marker, label = m.group(1), m.group(2)
            if marker == "x":
                correct.append(len(choices))
            choices.append(label)
            continue

        # Numeric answer
        m = _NUMERIC_RE.match(stripped)
        if m:
            qtype = "numeric"
            correct = float(m.group(1).strip())
            continue

        # Start of explanation block
        if stripped.startswith(">") and qtype is not None:
            in_explanation = True
            explanation_lines.append(stripped[1:].strip())
            continue

    explanation = "\n".join(explanation_lines).strip() or None

    return {
        "type": qtype or "radio",
        "choices": choices if choices else None,
        "correct": correct,
        "explanation": explanation,
    }


def _split_questions(body: str) -> list[tuple[str, str]]:
    """Split quiz body into (question_id, section_text) pairs."""
    parts = _QUESTION_RE.split(body)
    # parts[0] is text before first question (ignored)
    # then alternating: id, section_text, id, section_text, ...
    questions = []
    for i in range(1, len(parts), 2):
        qid = parts[i]
        section = parts[i + 1] if i + 1 < len(parts) else ""
        questions.append((qid, section))
    return questions


def _validate_quiz_file(quiz_file: str) -> Path:
    """Validate and resolve quiz file path. Raises ValueError on bad input."""
    if "/" in quiz_file or "\\" in quiz_file or ".." in quiz_file:
        raise ValueError("Invalid quiz file name")
    if not quiz_file.endswith(".md"):
        raise ValueError("Quiz file must end with .md")
    path = _quiz_dir() / quiz_file
    if not path.is_file():
        raise ValueError(f"Quiz not found: {quiz_file}")
    return path


# ── RPC Functions ──


@noregcheck
@nolog
def list_quizzes() -> list[dict]:
    """Return available quizzes: [{file, title}, ...]."""
    quiz_dir = _quiz_dir()
    if not quiz_dir.is_dir():
        return []
    results = []
    for p in sorted(quiz_dir.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        fm, _ = _parse_frontmatter(text)
        results.append({
            "file": p.name,
            "title": fm.get("title", p.stem),
        })
    return results


@noregcheck
@nolog
def get_quiz(quiz_file: str) -> dict:
    """Return quiz with correct answers stripped.

    Returns {frontmatter: {...}, body: "stripped markdown"}.
    """
    path = _validate_quiz_file(quiz_file)
    text = path.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(text)

    # Strip correct-answer markers so students can't see them
    stripped_lines = []
    for line in body.split("\n"):
        s = line.strip()
        # (x) → ( )
        if _RADIO_RE.match(s) and "(x)" in s:
            line = line.replace("(x)", "( )", 1)
        # [x] → [ ]
        elif _CHECK_RE.match(s) and "[x]" in s:
            line = line.replace("[x]", "[ ]", 1)
        # = answer → = ???
        elif _NUMERIC_RE.match(s):
            line = re.sub(r"^(\s*=\s+).*$", r"\g<1>???", line)
        stripped_lines.append(line)

    return {
        "frontmatter": fm,
        "body": "\n".join(stripped_lines),
    }


def grade(quiz_file: str, question_id: str, answer) -> dict:
    """Grade a single question.

    Args:
        quiz_file: Quiz filename (e.g. "derivatives.md").
        question_id: Question identifier from the header.
        answer: int (radio index), list[int] (checkbox indices), or float (numeric).

    Returns:
        {correct: bool, expected: ..., explanation: str|None}
    """
    path = _validate_quiz_file(quiz_file)
    text = path.read_text(encoding="utf-8")
    _, body = _parse_frontmatter(text)

    questions = _split_questions(body)
    for qid, section in questions:
        if qid == question_id:
            parsed = _parse_question(section)
            expected = parsed["correct"]
            explanation = parsed["explanation"]

            if parsed["type"] == "numeric":
                # Float comparison with tolerance
                try:
                    student_val = float(answer)
                except (TypeError, ValueError):
                    return {"correct": False, "expected": expected, "explanation": explanation}
                tol = max(1e-6, abs(expected) * 1e-6)
                correct = math.isclose(student_val, expected, abs_tol=tol)
            elif parsed["type"] == "checkbox":
                # Compare sorted index lists
                if not isinstance(answer, list):
                    answer = [answer]
                correct = sorted(answer) == sorted(expected)
            else:
                # Radio — compare single index
                correct = answer == expected

            return {
                "correct": correct,
                "expected": expected,
                "explanation": explanation,
            }

    raise ValueError(f"Question not found: {question_id}")
