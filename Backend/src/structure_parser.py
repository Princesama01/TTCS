import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class StructureNode:
    level: str
    number: str
    title: str
    content: str
    article_no: str = ""
    clause_no: Optional[str] = None
    point_no: Optional[str] = None
    structure_path: str = ""
    char_start: int = 0
    char_end: int = 0
    children: List["StructureNode"] = field(default_factory=list)


class LegalStructureParser:
    ARTICLE_RE = re.compile(r"(?:Điều|Dieu)\s+(\d+)\.\s*(.+?)(?:\n|$)", re.UNICODE)
    CLAUSE_RE = re.compile(r"^(\d+\.\d+)\.\s*(.+)", re.MULTILINE | re.UNICODE)
    POINT_RE = re.compile(r"^\s+([a-zA-Z])\)\s*(.+)", re.MULTILINE | re.UNICODE)

    def parse(self, text: str) -> List[StructureNode]:
        return [self._parse_article(art, text) for art in self._split_articles(text)]

    def _split_articles(self, text: str) -> List[dict]:
        matches = list(self.ARTICLE_RE.finditer(text))
        articles = []
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            articles.append(
                {
                    "number": m.group(1),
                    "title": m.group(2).strip(),
                    "body": text[m.end() : end].strip(),
                    "full": text[start:end].strip(),
                    "char_start": start,
                    "char_end": end,
                }
            )
        return articles

    def _parse_article(self, art: dict, _full_text: str) -> StructureNode:
        art_no = art["number"]
        node = StructureNode(
            level="article",
            number=art_no,
            title=art["title"],
            content=art["full"],
            article_no=art_no,
            structure_path=f"Điều {art_no}",
            char_start=art["char_start"],
            char_end=art["char_end"],
        )
        node.children = self._extract_clauses(art["body"], art_no, art["char_start"])
        return node

    def _extract_clauses(self, body: str, article_no: str, offset: int) -> List[StructureNode]:
        matches = list(self.CLAUSE_RE.finditer(body))
        clauses = []
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
            clause_text = body[start:end].strip()
            clause_num = m.group(1)
            clause_node = StructureNode(
                level="clause",
                number=clause_num,
                title=m.group(2).strip()[:80],
                content=clause_text,
                article_no=article_no,
                clause_no=clause_num,
                structure_path=f"Điều {article_no}/{clause_num}",
                char_start=offset + start,
                char_end=offset + end,
            )
            clause_node.children = self._extract_points(clause_text, article_no, clause_num, offset + start)
            clauses.append(clause_node)
        return clauses

    def _extract_points(self, clause_text: str, article_no: str, clause_no: str, offset: int) -> List[StructureNode]:
        matches = list(self.POINT_RE.finditer(clause_text))
        points = []
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(clause_text)
            point_id = m.group(1)
            points.append(
                StructureNode(
                    level="point",
                    number=point_id,
                    title=m.group(2).strip()[:80],
                    content=clause_text[start:end].strip(),
                    article_no=article_no,
                    clause_no=clause_no,
                    point_no=point_id,
                    structure_path=f"Điều {article_no}/{clause_no}/{point_id}",
                    char_start=offset + start,
                    char_end=offset + end,
                )
            )
        return points
