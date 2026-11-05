#!/usr/bin/env python3
"""Daily BRAIN email research archive.

Searches both Gmail Inbox and Spam through the read-only Codex Gmail connector,
reads full messages, and maintains the local archive.  This is intentionally a
deterministic file-only job: it never opens DuckDB, starts/stops the simulation
service, sends email, changes labels/read state, or executes message content.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain_gmail_connector import CodexGmail

ARCHIVE = Path(__file__).resolve().parents[1] / "docs" / "forum" / "brain_email_ideas_20261021"
MESSAGES = ARCHIVE / "messages"
BASE_QUERY = '{from:worldquantbrain.com from:worldquant.com from:worldquantbrain.zendesk.com "WorldQuant BRAIN"}'
COMBINED_QUERY = "{in:inbox in:spam} " + BASE_QUERY
FOLDER_QUERIES = {"inbox": "in:inbox " + BASE_QUERY, "spam": "in:spam " + BASE_QUERY}
MAX_PAGES = 50
PAGE_SIZE = 100
DEFAULT_MAX_NEW = 80

CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    (
        "options",
        (
            "option",
            "期权",
            "implied volatility",
            "隐含波动率",
            "open interest",
            "持仓量",
            "strike",
            "行权价",
            "call-put",
            "看涨期权",
            "看跌期权",
        ),
    ),
    (
        "shortinterest",
        ("short interest", "shortinterest", "securities lending", "借券", "融券", "borrow fee", "卖空比例", "空头持仓"),
    ),
    ("insiders", ("insider", "内部人", "insider trading", "内幕交易")),
    ("institutions", ("13f", "机构持股", "institutional ownership", "institution ownership")),
    ("earnings", ("earnings", "财报", "eps", "guidance", "财季", "业绩预告")),
    (
        "fundamental",
        (
            "revenue",
            "营收",
            "book value",
            "账面价值",
            "fcf",
            "自由现金流",
            "valuation",
            "估值",
            "pe ratio",
            "市盈率",
            "total assets",
            "总资产",
        ),
    ),
    ("sentiment", ("sentiment", "情绪", "语调", "news sentiment", "舆情")),
    ("news", ("news", "新闻", "headline", "头条", "事件驱动")),
    ("risk", ("risk model", "风险模型", "covariance", "协方差", "volatility", "波动率", "drawdown", "回撤")),
    (
        "model",
        (
            "machine learning",
            "机器学习",
            "prediction",
            "预测模型",
            "cnn",
            "transformer",
            "neural network",
            "神经网络",
            "model score",
            "模型评分",
        ),
    ),
    (
        "pv",
        (
            "price",
            "价格",
            "volume",
            "成交量",
            "turnover",
            "换手率",
            "reversal",
            "反转",
            "momentum",
            "动量",
            "ohlcv",
            "vwap",
        ),
    ),
    ("mixed_paper_hypotheses", ("arxiv", "literature", "文献", "论文")),
]
METHODOLOGY_SUBJECT_TAGS = (
    "alpha agent workflow",
    "工作流",
    "prompt",
    "mcp",
    "python alpha",
    "经验分享",
    "研究方法",
    "回测",
    "模板",
    "方法论",
    "研究记录",
    "实验设计",
    "消融",
    "ablation",
    "工具",
    "代码",
    "agent",
    "sub agent",
    "skills",
    "cli",
    "安装",
    "配置",
    "环境",
    "报错",
    "解决",
    "脚本",
    "工作台",
    "助手",
    "pnl",
    "哈希",
    "因子构造",
    "因子筛选",
    "表达式",
    "复盘",
    "combined",
    "为什么ai",
    "vf",
    "提交总结",
)
FOOTER_MARKERS = (
    "You are receiving this notification",
    "Please do not reply to this message",
    "This email is a service from WorldQuant BRAIN",
    "The information contained in this communication is confidential",
    "If you want to stop these notifications",
)
URL_RE = re.compile(r"https?://[^\s<>\"')\]]+", re.I)
UNSUB_URL_RE = re.compile(
    r"https?://[^\s<>\"')\]]*(?:unsubscribe|opt[-_]?out|preferences|subscription|email[-_]?settings)[^\s<>\"')\]]*",
    re.I,
)
UNSUB_MAILTO_RE = re.compile(r"mailto:[^\s<>\"']*(?:unsubscribe|opt[-_]?out)[^\s<>\"']*", re.I)
FORUM_TEXT_RE = re.compile(r"View the post\s*\((https://support\.worldquantbrain\.com/[^\s)]+)\)", re.I)
FORUM_HTML_RE = re.compile(r"href=[\"\'](https://support\.worldquantbrain\.com/hc/[^\"\']*/posts/[^\"\']+)[\"\']", re.I)
POST_ID_RE = re.compile(r"/posts/(\d+)")
AUTHOR_RE = re.compile(r"\bby\s+([A-Za-z][A-Za-z0-9_.\-]{1,40})\s*(?:\r?\n|$)")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._skip += 1
        elif tag in {"br", "p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip:
            self._skip -= 1
        elif tag in {"p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


class _CodeBlocks(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.buffer: list[str] = []
        self.blocks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "pre":
            if self.depth == 0:
                self.buffer = []
            self.depth += 1
        elif self.depth and tag == "br":
            self.buffer.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == "pre" and self.depth:
            self.depth -= 1
            if not self.depth:
                self.blocks.append("".join(self.buffer).strip())

    def handle_data(self, data: str) -> None:
        if self.depth:
            self.buffer.append(data)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        return default


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def write_json(path: Path, value: Any) -> None:
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def header_map(payload: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for header in payload.get("headers") or []:
        name = str(header.get("name") or "").strip().lower()
        value = str(header.get("value") or "")
        if name and name not in result:
            result[name] = value
    return result


def mime_of(node: dict[str, Any]) -> str:
    value = str(node.get("mime_type") or "").split(";")[0].strip().lower()
    if value:
        return value
    return header_map(node).get("content-type", "").split(";")[0].strip().lower()


def decode_body(body: dict[str, Any]) -> str:
    content = body.get("content")
    if content:
        return str(content)
    encoded = body.get("base64_url_content")
    if encoded:
        try:
            return base64.urlsafe_b64decode(str(encoded)).decode("utf-8", "replace")
        except Exception:
            return ""
    return ""


def extract_parts(node: dict[str, Any]) -> list[dict[str, str]]:
    parts: list[dict[str, str]] = []
    mime = mime_of(node)
    filename = str(node.get("filename") or "")
    body = node.get("body") or {}
    if mime.startswith("text/") and not filename:
        content = decode_body(body)
        if content:
            parts.append({"mime_type": mime, "content": content})
        return parts
    if mime.startswith("multipart/") or node.get("parts"):
        for child in node.get("parts") or []:
            parts.extend(extract_parts(child))
        return parts
    if not mime and body:
        content = decode_body(body)
        if content:
            inferred = "text/html" if content.lstrip().startswith("<") else "text/plain"
            parts.append({"mime_type": inferred, "content": content})
    return parts


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(html)
    except Exception:
        return re.sub(r"<[^>]+>", " ", html)
    text = "".join(parser.parts)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def scrub_unsubscribe(text: str, is_html: bool) -> str:
    if not text:
        return text
    if is_html:
        text = re.sub(
            r"<a\b[^>]*href=[\"'][^\"']*(?:unsubscribe|opt[-_]?out|preferences)[^\"']*[\"'][^>]*>.*?</a>",
            "[personal unsubscribe link removed]",
            text,
            flags=re.I | re.S,
        )
    text = UNSUB_URL_RE.sub("[personal unsubscribe link removed]", text)
    text = UNSUB_MAILTO_RE.sub("[personal unsubscribe link removed]", text)
    lines = []
    for line in text.splitlines():
        if len(line) < 220 and re.search(r"(?i)\bunsubscribe\b.*\bpreferences?\b", line):
            continue
        lines.append(line)
    return "\n".join(lines)


def strip_footer(text: str) -> str:
    cleaned = text or ""
    for marker in FOOTER_MARKERS:
        index = cleaned.find(marker)
        if index > 200:
            cleaned = cleaned[:index]
    cleaned = re.sub(r"(?m)^#{10,}\s*$", "", cleaned)
    cleaned = re.sub(r"(?m)^-{10,}\s*$", "", cleaned)
    return cleaned.strip()


def sanitize_message(source: dict[str, Any]) -> bool:
    """Remove personal unsubscribe links from an already-saved message."""
    changed = False
    for part in source.get("parts") or []:
        old = str(part.get("content") or "")
        new = scrub_unsubscribe(old, part.get("mime_type") == "text/html")
        if new != old:
            part["content"] = new
            changed = True
    for key in ("snippet", "article_text"):
        old = source.get(key)
        if isinstance(old, str):
            new = scrub_unsubscribe(old, False)
            if new != old:
                source[key] = new
                changed = True
    if str(source.get("archived_at_utc") or "").startswith(utc_now()[:10]):
        categories = categorize(source.get("subject", ""), source.get("article_text", "") or "")
        if source.get("research_categories") != categories:
            source["research_categories"] = categories
            changed = True
    return changed


def sanitize_archive() -> int:
    changed_count = 0
    for path in sorted(MESSAGES.glob("*.json")):
        try:
            source = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if sanitize_message(source):
            write_json(path, source)
            changed_count += 1
    return changed_count


def prune_today_non_research() -> list[str]:
    """Remove only messages archived today that fail the research screen.

    Pre-existing archive files (older archived_at_utc) are never touched.
    """
    removed: list[str] = []
    today = utc_now()[:10]
    for path in sorted(MESSAGES.glob("*.json")):
        try:
            source = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if not str(source.get("archived_at_utc") or "").startswith(today):
            continue
        candidate, _ = is_research_candidate(source)
        if not candidate:
            path.unlink()
            removed.append(str(source.get("id") or path.stem))
    return removed


def gmail_url(message_id: str) -> str:
    return f"https://mail.google.com/mail/u/?authuser=victor000000%40gmail.com#all/{message_id}"


def iso_from_internal(value: Any) -> str | None:
    try:
        number = int(str(value))
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    return datetime.fromtimestamp(number / 1000, UTC).isoformat()


def iso_from_header(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat()


def timestamp(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip()
    if not text:
        return 0.0
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def extract_forum(plain: str, html: str) -> tuple[str | None, str | None]:
    match = FORUM_TEXT_RE.search(plain or "") or FORUM_HTML_RE.search(html or "")
    if not match:
        return None, None
    url = unescape(match.group(1))
    post = POST_ID_RE.search(url)
    return url, post.group(1) if post else None


def extract_author(plain: str) -> str | None:
    head = (plain or "")[:3000]
    match = AUTHOR_RE.search(head)
    return match.group(1) if match else None


def categorize(subject: str, text: str) -> list[str]:
    """Conservative subject/content tags; never a native pyramid claim."""
    subject_l = (subject or "").lower()
    blob = (subject + "\n" + (text or "")[:30000]).lower()
    if any(tag in subject_l for tag in METHODOLOGY_SUBJECT_TAGS):
        return ["research_methodology"]
    matched: list[tuple[str, int]] = []
    for category, keywords in CATEGORY_RULES:
        hits = sum(1 for keyword in keywords if keyword in blob)
        if hits:
            matched.append((category, hits))
    matched.sort(key=lambda item: item[1], reverse=True)
    categories = [category for category, hits in matched if hits >= 2][:3]
    if not categories and matched:
        categories = [matched[0][0]]
    if not categories:
        categories = ["unclassified"]
    return categories


def is_research_candidate(meta: dict[str, Any]) -> tuple[bool, str]:
    """Broad research relevance screen; never a native-category claim.

    Administrative mail (billing, courses, contests, recruiting, freebies) is
    left at metadata-only.  Forum research posts and the Alpha Ideas Series are
    selected for full reading.
    """
    subject = str(meta.get("subject") or "")
    if not subject:
        return False, "missing subject"
    lower = subject.lower()
    whitelist = ("alpha agent workflow", "alpha idea", "alpha ideas series", "投研逻辑")
    hard_administrative = (
        "春节",
        "假期",
        "收入回顾",
        "课程",
        "培训",
        "通知",
        "公告",
        "招聘",
        "账单",
        "发票",
        "workday",
        "payment",
        "报名",
        "公开课",
        "答疑",
        "会议",
        "直播",
        "回放",
        "iqc",
        "竞赛",
        "比赛",
        "羊毛",
        "福利",
        "免费",
        "订阅",
        "spotlight",
        "congratulations",
        "webinar",
        "spc",
        "arc 2026",
        "祝贺",
        "定级",
        "榜单",
        "排名",
        "喜报",
        "确认",
        "注册",
    )
    if any(token in lower for token in hard_administrative) and not any(token in lower for token in whitelist):
        return False, "administrative/non-research marker"
    strong = (
        "Alpha Idea",
        "Alpha Ideas Series",
        "Alpha Agent Workflow",
        "Alpha灵感",
        "经验分享",
        "工作流",
        "Python Alpha",
        "研究工作流",
        "回测",
        "因子",
        "数据集",
        "字段",
        "模板",
        "研究",
        "alpha",
        "sharpe",
        "combined",
        "prod",
        "vf",
        "mcp",
        "wqclient",
        "spiderpanel",
        "点塔",
        "数据获取",
        "量化日记",
    )
    if any(token.lower() in lower for token in strong):
        return True, "research keyword in subject"
    if "顾问专属中文论坛" in subject:
        return True, "forum community post without administrative marker"
    return False, "administrative/non-research subject"


def article_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_message(message: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    payload = message.get("payload") or {}
    headers = header_map(payload)
    message_id = str(message.get("id") or meta.get("id"))
    parts = extract_parts(payload)
    plain = "\n".join(part["content"] for part in parts if part["mime_type"] == "text/plain")
    html = "\n".join(part["content"] for part in parts if part["mime_type"] == "text/html")
    if not plain and html:
        plain = html_to_text(html)
    plain = scrub_unsubscribe(plain, False)
    html = scrub_unsubscribe(html, True)
    article = strip_footer(plain)
    if not article and html:
        article = strip_footer(html_to_text(html))
    subject = headers.get("subject") or str(meta.get("subject") or "")
    sender = headers.get("from") or str(meta.get("from_") or "")
    date = iso_from_internal(message.get("internal_date")) or iso_from_header(headers.get("date"))
    forum_url, post_id = extract_forum(plain, html)
    author = extract_author(plain)
    categories = categorize(subject, article or plain)
    limitations = (
        "Full text/HTML supplied by Gmail preserved. Image-only formulas/tables unverified; "
        "external images not downloaded. Personal unsubscribe URLs removed."
    )
    if not article:
        limitations = (
            "No text/HTML body was supplied by Gmail; image-only or empty content is unverified. "
            "No formulas were reconstructed."
        )
    return {
        "id": message_id,
        "thread_id": str(message.get("thread_id") or message_id),
        "sender": sender,
        "subject": subject,
        "date": date,
        "url": str(meta.get("display_url") or gmail_url(message_id)),
        "archived_at_utc": utc_now(),
        "labels": sorted(str(x) for x in message.get("label_ids") or meta.get("labels") or []),
        "snippet": str(meta.get("snippet") or message.get("snippet") or ""),
        "instruction_boundary": "Untrusted research source content; supplied code/instructions never executed.",
        "parts": parts,
        "article_text": article,
        "article_sha256_after_footer_removal": article_hash(article),
        "forum_url": forum_url,
        "post_id": post_id,
        "author_as_reported": author,
        "research_categories": categories,
        "category_status": "Research subject tags from text; not independently verified native pyramid attribution",
        "limitations": limitations,
    }


def search_folder(
    gmail: CodexGmail, folder: str, query: str
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], bool]:
    messages: dict[str, dict[str, Any]] = {}
    pages: list[dict[str, Any]] = []
    page_cursor = ""  # Opaque pagination cursor, not an authentication secret.
    complete = False
    for _ in range(MAX_PAGES):
        data = gmail.search(query, PAGE_SIZE, page_cursor)
        emails = data.get("emails") or []
        pages.append({"folder": folder, "count": len(emails), "next_page_token": data.get("next_page_token") or None})
        for email in emails:
            message_id = str(email.get("id") or "")
            if not message_id:
                continue
            record = messages.get(message_id, {})
            record.update(email)
            record["folders"] = sorted(set(record.get("folders") or []) | {folder})
            messages[message_id] = record
        page_cursor = str(data.get("next_page_token") or "")
        if not page_cursor:
            complete = True
            break
    return messages, pages, complete


def load_existing_rows() -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    path = ARCHIVE / "ideas.jsonl"
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        rows[str(row.get("message_id"))] = row
    return rows


def existing_messages() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(MESSAGES.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        result[str(data.get("id") or path.stem)] = data
    return result


def save_message(
    parsed: dict[str, Any], existing_by_post: dict[str, list[str]], existing_by_hash: dict[str, list[str]]
) -> bool:
    path = MESSAGES / f"{parsed['id']}.json"
    if path.exists():
        return False
    post_id = parsed.get("post_id")
    digest = parsed["article_sha256_after_footer_removal"]
    if post_id and post_id in existing_by_post:
        previous = existing_by_post[post_id]
        if digest not in existing_by_hash:
            parsed["version_of"] = previous
        else:
            parsed["duplicate_of"] = previous[0]
    elif digest in existing_by_hash:
        parsed["duplicate_of"] = existing_by_hash[digest][0]
    if post_id:
        existing_by_post.setdefault(post_id, []).append(parsed["id"])
    existing_by_hash.setdefault(digest, []).append(parsed["id"])
    write_json(path, parsed)
    return True


def rebuild(run_meta: dict[str, Any]) -> dict[str, Any]:
    old_rows = load_existing_rows()
    messages = existing_messages()
    rows: list[dict[str, Any]] = []
    post_map: dict[str, list[str]] = defaultdict(list)
    hash_map: dict[str, list[str]] = defaultdict(list)
    subject_map: dict[str, list[str]] = defaultdict(list)
    for message_id, source in sorted(messages.items(), key=lambda item: (str(item[1].get("date") or ""), item[0])):
        old = old_rows.get(message_id, {})
        parts = source.get("parts") or []
        plain = "\n".join(part.get("content", "") for part in parts if part.get("mime_type") == "text/plain")
        html = "\n".join(part.get("content", "") for part in parts if part.get("mime_type") == "text/html")
        article = old.get("article_text")
        if article is None:
            article = strip_footer(plain)
            if not article and html:
                article = strip_footer(html_to_text(html))
        article = scrub_unsubscribe(article or "", False)
        forum_url = old.get("forum_url") or source.get("forum_url")
        post_id = old.get("post_id") or source.get("post_id")
        if not forum_url:
            forum_url, extracted_post = extract_forum(plain, html)
            post_id = post_id or extracted_post
        author = old.get("author_as_reported") or source.get("author_as_reported") or extract_author(plain)
        parser = _CodeBlocks()
        if html:
            with contextlib.suppress(ValueError, TypeError):
                parser.feed(html)
        blocks = old.get("html_code_blocks_unvalidated")
        if blocks is None:
            blocks = parser.blocks
        blocks = [scrub_unsubscribe(str(block), False) for block in blocks]
        images = old.get("external_image_urls_uninspected")
        if images is None:
            images = sorted(set(re.findall(r"<img[^>]+src=[\"\']([^\"\']+)", html)))
        digest = article_hash(article)
        source_path = MESSAGES / f"{message_id}.json"
        row = {
            "message_id": message_id,
            "subject": source.get("subject", ""),
            "sender": source.get("sender", ""),
            "date": source.get("date"),
            "author_as_reported": author,
            "gmail_url": source.get("url") or gmail_url(message_id),
            "forum_url": forum_url,
            "post_id": post_id,
            "source_file": f"messages/{message_id}.json",
            "source_file_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
            "article_sha256_after_footer_removal": digest,
            "article_text": article,
            "html_code_blocks_unvalidated": blocks,
            "external_image_urls_uninspected": images,
            "categories": source.get("research_categories") or old.get("categories") or ["unclassified"],
            "simulation_authorized": False,
            "validation_status": "ARCHIVED_SOURCE_ONLY_NOT_REPRODUCED",
            "version_of": source.get("version_of") or old.get("version_of") or [],
            "duplicate_of": source.get("duplicate_of") or old.get("duplicate_of"),
        }
        rows.append(row)
        if post_id:
            post_map[post_id].append(message_id)
        hash_map[digest].append(message_id)
        subject_map[str(row["subject"])].append(message_id)

    write_text(
        ARCHIVE / "ideas.jsonl",
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
    )
    checkpoint = {
        "built_at_utc": utc_now(),
        "archived_messages": len(rows),
        "unique_post_ids": len({row["post_id"] for row in rows if row["post_id"]}),
        "unique_article_text_hashes": len(hash_map),
        "duplicate_post_message_ids": {key: value for key, value in post_map.items() if len(value) > 1},
        "same_article_message_ids": {key: value for key, value in hash_map.items() if len(value) > 1},
        "same_subject_possible_reposts": {key: value for key, value in subject_map.items() if len(value) > 1},
        "category_counts": dict(Counter(category for row in rows for category in row["categories"])),
        "saved_message_ids": sorted(messages),
        "image_only_limit": "Image URLs preserved; image-only equations/tables are uninspected, not reconstructed.",
        "scope": "Archive ALL research categories. Simulations remain PV/options-only under separate authorization.",
        "daily_automation_id": "save-brain-email-ideas-daily",
        "daily_review_time": "11:00 Asia/Shanghai",
        "status": "ACTIVE",
        "archive": str(ARCHIVE.name),
        "connector": "Codex app-server codex_apps Gmail read-only tools",
        "schedule": "DSH schedule daily 11:00 Asia/Shanghai",
        "last_run_utc": run_meta.get("finished_at_utc"),
        "last_run_new_messages": run_meta.get("new_messages_saved", 0),
        "backlog_remaining": run_meta.get("backlog_remaining", 0),
        "version_history": {key: value for key, value in post_map.items() if len(value) > 1},
    }
    write_json(ARCHIVE / "checkpoint.json", checkpoint)
    readme = render_readme(rows, checkpoint, run_meta)
    write_text(ARCHIVE / "README.md", readme)
    return {"rows": rows, "checkpoint": checkpoint}


def render_readme(rows: list[dict[str, Any]], checkpoint: dict[str, Any], run_meta: dict[str, Any]) -> str:
    lines = [
        "# BRAIN email research archive",
        "",
        "**Active.** Daily Gmail Inbox + Spam review at 11:00 Asia/Shanghai via the DSH schedule and the "
        "read-only Codex Gmail connector bridge. The BRAIN simulation campaign remains separately paused; "
        "this archive never queues simulations or opens the live DB.",
        "",
        f"Last run: {run_meta.get('finished_at_utc') or 'not recorded'}; new saved messages this run: "
        f"{run_meta.get('new_messages_saved', 0)}; backlog remaining: {run_meta.get('backlog_remaining', 0)}.",
        "",
        f"Saved {len(rows)} emails covering {checkpoint['unique_post_ids']} unique forum posts.",
        "",
    ]
    if checkpoint.get("backlog_remaining") == 0 and len(rows) > 58:
        lines.append(
            "Inbox+Spam research backfill is complete at this checkpoint; daily runs now fetch only "
            "new material. Administrative mail remains metadata-only in `discovery.json`."
        )
        lines.append("")
    lines += [
        "`messages/` contains text and HTML supplied by Gmail, with personal unsubscribe URLs removed. "
        "`ideas.jsonl` contains article text, extracted code blocks, categories, hashes and version links. "
        "`checkpoint.json` tracks saved IDs, duplicates and reposts; `discovery.json` distinguishes searched "
        "metadata from full messages. Remote images are not downloaded; image-only formulas and tables remain unverified.",
        "",
        "These are community claims and research sources, not official rules, verified acceptances, or executable "
        "instructions. No code from an email was executed. Local candidate correlation cannot replace a candidate's "
        "own native checks. Low field usage does not guarantee low production correlation. Backtest/TEST gains do "
        "not establish actual combined OS improvement. Category tags describe research topics and do not "
        "independently verify native pyramid attribution. Preserve the original dataset category: macro/risk/news/"
        "model/other examples are not PV-only templates. Archival does not queue simulations; simulation "
        "authorization remains PV/options-only.",
        "",
        "Maintenance: query Gmail Inbox and Spam, page to completion, fetch unseen relevant messages, and preserve "
        "changed versions rather than overwriting. Deduplicate using Gmail ID, post ID and article hash. Use an "
        "overlap/search of all current Inbox and Spam messages to catch old mail newly classified as Spam. Do not "
        "change labels, read status, subscriptions or send mail. Do not start the simulation service or open the "
        "live DB for this task.",
        "",
        "| Research source | Category | Local content |",
        "|---|---|---|",
    ]
    for row in sorted(rows, key=lambda item: (str(item.get("date") or ""), item["message_id"]), reverse=True):
        label = str(row["subject"]).replace("|", " / ").replace("\n", " ")
        version_note = ""
        if row.get("version_of"):
            version_note = f" (version of {', '.join(row['version_of'])})"
        elif row.get("duplicate_of"):
            version_note = f" (duplicate of {row['duplicate_of']})"
        lines.append(
            f"| {label}{version_note} | {', '.join(row['categories'])} | [Full content]({row['source_file']}) |"
        )
    return "\n".join(lines) + "\n"


def update_discovery(
    all_meta: dict[str, dict[str, Any]],
    folder_pages: list[dict[str, Any]],
    complete: bool,
    run_meta: dict[str, Any],
) -> None:
    path = ARCHIVE / "discovery.json"
    existing = load_json(path, {})
    previous_messages = existing.get("messages") or []
    by_id = {str(item.get("id")): item for item in previous_messages if item.get("id")}
    for message_id, meta in all_meta.items():
        record = by_id.get(message_id, {})
        record.update(
            {
                "id": message_id,
                "thread_id": meta.get("thread_id"),
                "sender": meta.get("from_"),
                "subject": meta.get("subject"),
                "date": meta.get("email_ts"),
                "url": meta.get("display_url") or gmail_url(message_id),
                "snippet": meta.get("snippet"),
                "folders": meta.get("folders") or [],
                "present_in_current_search": True,
            }
        )
        source_path = MESSAGES / f"{message_id}.json"
        record["full_content_saved"] = source_path.exists()
        record["source_file"] = f"messages/{message_id}.json" if source_path.exists() else None
        candidate, reason = is_research_candidate(meta)
        record["research_candidate"] = candidate
        record["relevance_reason"] = reason
        record["review_status"] = (
            "FULL_CONTENT_ARCHIVED"
            if source_path.exists()
            else ("METADATA_REVIEWED_RESEARCH_CANDIDATE" if candidate else "EXCLUDED_NON_RESEARCH")
        )
        by_id[message_id] = record
    for message_id, record in by_id.items():
        if message_id not in all_meta:
            record["present_in_current_search"] = False
    messages = list(by_id.values())
    update = {
        "query": COMBINED_QUERY,
        "folder_queries": {folder: query for folder, query in FOLDER_QUERIES.items()},
        "search_pages": folder_pages,
        "search_complete": complete,
        "metadata_only_unless_message_file_exists": True,
        "messages": messages,
        "full_messages_archived": sum(1 for item in messages if (MESSAGES / f"{item['id']}.json").exists()),
        "metadata_messages_reviewed": len(messages),
        "updated_at_utc": utc_now(),
        "selection_note": existing.get(
            "selection_note",
            "Metadata identifies candidates; full messages are archived only after read_email/batch_read_email.",
        ),
        "last_run": run_meta,
    }
    if existing.get("query") and existing.get("query") != COMBINED_QUERY:
        update["previous_query"] = existing.get("query")
        update["previous_search_pages"] = existing.get("search_pages")
    write_json(path, update)


def update_verification(rows: list[dict[str, Any]], run_meta: dict[str, Any]) -> None:
    source_hashes_match = True
    for row in rows:
        path = ARCHIVE / row["source_file"]
        try:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
        except Exception:
            source_hashes_match = False
            continue
        if actual != row["source_file_sha256"]:
            source_hashes_match = False
    unsubscribe_left = False
    for path in MESSAGES.glob("*.json"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if UNSUB_URL_RE.search(text):
            unsubscribe_left = True
            break
    verification = {
        "checked_at_utc": utc_now(),
        "metadata_reviewed": len(load_json(ARCHIVE / "discovery.json", {}).get("messages") or []),
        "full_messages_saved": len(rows),
        "unique_post_ids": len({row["post_id"] for row in rows if row["post_id"]}),
        "article_characters": sum(len(row["article_text"]) for row in rows),
        "extracted_html_code_blocks": sum(len(row["html_code_blocks_unvalidated"]) for row in rows),
        "source_hashes_match": source_hashes_match,
        "all_tagged_idea_titles_archived": all((ARCHIVE / row["source_file"]).exists() for row in rows),
        "personal_unsubscribe_urls_removed": not unsubscribe_left,
        "database_access": False,
        "email_mutations": False,
        "source_code_executed": False,
        "external_images": "URLs archived; contents unverified",
        "automation_id": "save-brain-email-ideas-daily",
        "connector": "Codex app-server codex_apps Gmail read-only tools",
        "last_run_new_messages": run_meta.get("new_messages_saved", 0),
        "last_run_utc": run_meta.get("finished_at_utc"),
    }
    write_json(ARCHIVE / "verification.json", verification)


def update_workflow_status(run_meta: dict[str, Any]) -> None:
    path = ARCHIVE / "workflow_status.json"
    status = load_json(path, {})
    status.update(
        {
            "updated_at_utc": utc_now(),
            "status": "ACTIVE",
            "automation_id": "save-brain-email-ideas-daily",
            "schedule": "DSH schedule daily 11:00 Asia/Shanghai",
            "schedule_timezone": "Asia/Shanghai",
            "schedule_local_time": "11:00",
            "folders": ["INBOX", "SPAM"],
            "query": COMBINED_QUERY,
            "archive_categories": "ALL",
            "simulation_scope": "PV/options only; simulation goal separately paused",
            "initial_archive_scope": "Spam-only first batch (58 messages); Inbox+Spam backfill completed; see checkpoint",
            "source_of_truth": "docs/EMAIL_RESEARCH.md",
            "explicit_user_resume_required": False,
            "connector": "Codex app-server codex_apps Gmail read-only tools",
            "last_run_utc": run_meta.get("finished_at_utc"),
            "last_run_new_messages": run_meta.get("new_messages_saved", 0),
            "backlog_remaining": run_meta.get("backlog_remaining", 0),
        }
    )
    write_json(path, status)


def run(max_new: int, dry_run: bool, prune: bool = False) -> dict[str, Any]:
    started = utc_now()
    all_meta: dict[str, dict[str, Any]] = {}
    folder_pages: list[dict[str, Any]] = []
    complete = True
    with CodexGmail() as gmail:
        for folder, query in FOLDER_QUERIES.items():
            messages, pages, folder_complete = search_folder(gmail, folder, query)
            folder_pages.extend(pages)
            complete = complete and folder_complete
            for message_id, meta in messages.items():
                record = all_meta.get(message_id, {})
                record.update(meta)
                record["folders"] = sorted(set(record.get("folders") or []) | {folder})
                all_meta[message_id] = record
        checkpoint = load_json(ARCHIVE / "checkpoint.json", {})
        removed_ids = prune_today_non_research() if (prune and not dry_run) else []
        saved_ids = set(str(x) for x in checkpoint.get("saved_message_ids") or [])
        saved_ids.update(path.stem for path in MESSAGES.glob("*.json"))
        saved_ids.difference_update(removed_ids)
        unseen_ids = [message_id for message_id in all_meta if message_id not in saved_ids]
        scored = {message_id: is_research_candidate(all_meta[message_id]) for message_id in unseen_ids}
        new_ids = [message_id for message_id in unseen_ids if scored[message_id][0]]
        excluded = [message_id for message_id in unseen_ids if not scored[message_id][0]]
        new_ids.sort(key=lambda item: timestamp(all_meta[item].get("email_ts")), reverse=True)
        selected = new_ids[:max_new]
        backlog = max(0, len(new_ids) - len(selected))
        summary: dict[str, Any] = {
            "started_at_utc": started,
            "finished_at_utc": None,
            "query": COMBINED_QUERY,
            "folders": {
                folder: len([1 for meta in all_meta.values() if folder in (meta.get("folders") or [])])
                for folder in FOLDER_QUERIES
            },
            "metadata_messages": len(all_meta),
            "already_saved": len(saved_ids & set(all_meta)),
            "unseen_messages": len(unseen_ids),
            "new_candidates": len(new_ids),
            "metadata_excluded_non_research": len(excluded),
            "selected_for_full_read": len(selected),
            "backlog_remaining": backlog,
            "new_messages_saved": 0,
            "pruned_non_research": removed_ids,
            "errors": [],
            "search_complete": complete,
            "dry_run": dry_run,
            "new_ids_sample": selected[:10],
            "excluded_subjects_sample": [str(all_meta[item].get("subject") or "")[:120] for item in excluded[:5]],
        }
        if dry_run:
            summary["finished_at_utc"] = utc_now()
            return summary
        existing_by_post: dict[str, list[str]] = defaultdict(list)
        existing_by_hash: dict[str, list[str]] = defaultdict(list)
        old_rows = load_existing_rows()
        for row in old_rows.values():
            if row.get("post_id"):
                existing_by_post[str(row["post_id"])].append(str(row["message_id"]))
            if row.get("article_sha256_after_footer_removal"):
                existing_by_hash[str(row["article_sha256_after_footer_removal"])].append(str(row["message_id"]))
        MESSAGES.mkdir(parents=True, exist_ok=True)
        for message_id in selected:
            try:
                parsed = parse_message(gmail.read(message_id), all_meta.get(message_id, {}))
                if save_message(parsed, existing_by_post, existing_by_hash):
                    summary["new_messages_saved"] += 1
            except Exception as exc:  # archive must not abort on one bad message
                summary["errors"].append(f"{message_id}: {exc}")
    summary["finished_at_utc"] = utc_now()
    summary["sanitized_messages"] = sanitize_archive()
    rebuilt = rebuild(summary)
    update_discovery(all_meta, folder_pages, complete, summary)
    update_verification(rebuilt["rows"], summary)
    update_workflow_status(summary)
    write_json(ARCHIVE / "last_run.json", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    global ARCHIVE, MESSAGES
    with contextlib.suppress(AttributeError, OSError, ValueError):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-new", type=int, default=DEFAULT_MAX_NEW)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--prune-non-research", action="store_true")
    parser.add_argument("--archive-dir", type=Path, default=ARCHIVE)
    args = parser.parse_args(argv)
    ARCHIVE = args.archive_dir.resolve()
    MESSAGES = ARCHIVE / "messages"
    try:
        summary = run(max(0, args.max_new), args.dry_run, args.prune_non_research)
    except Exception as exc:
        error = {
            "failed_at_utc": utc_now(),
            "error": f"{type(exc).__name__}: {exc}",
            "archive": str(ARCHIVE),
        }
        print(json.dumps(error, ensure_ascii=False))
        return 1
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
