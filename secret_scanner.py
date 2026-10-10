"""Domestic secret scanner: parses .gitleaks.toml regexes and scans text."""
from __future__ import annotations
import re
import sys
from pathlib import Path

RULES_FILE = Path(__file__).resolve().parent / ".gitleaks.toml"

PLACEHOLDER_PATTERNS = [
    re.compile(r"sk-(your-key-here|x{4,}|\*+|test|example|1234)", re.IGNORECASE),
    re.compile(r"os\.getenv|process\.env|System\.getenv|Environment\.GetEnvironmentVariable"),
    re.compile(r"example\.example|x{4,}\.x{4,}|your-key", re.IGNORECASE),
    re.compile(r"://(user:pass(word)?|test:test)@", re.IGNORECASE),
]

RULES: list[tuple[str, re.Pattern]] = [
    ("deepseek-api-key", re.compile(r"sk-[a-f0-9]{32}")),
    ("moonshot-kimi-api-key", re.compile(r"sk-[a-zA-Z0-9]{48}")),
    ("dashscope-api-key", re.compile(r"sk-[a-f0-9]{32}")),
    ("zhipu-glm-api-key", re.compile(r"[a-zA-Z0-9]{32}\.[a-zA-Z0-9]{16,32}")),
    ("minimax-api-key", re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}")),
    ("minimax-group-key", re.compile(r"minimax.{0,20}key.{0,5}[:=]\s*['\"]?[A-Za-z0-9]{20,}['\"]?", re.IGNORECASE)),
    ("baidu-qianfan-altak", re.compile(r"ALTAK-[A-Za-z0-9_\-]{10,}")),
    ("baichuan-api-key", re.compile(r"sk-[a-zA-Z0-9]{32}")),
    ("generic-db-uri-with-password", re.compile(r"(mysql|postgres|postgresql|mongodb|redis|mssql)://[^/\s:]+:[^/\s@]+@[^\s'\"]+", re.IGNORECASE)),
    ("generic-private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
]


def is_placeholder(text: str) -> bool:
    return any(p.search(text) for p in PLACEHOLDER_PATTERNS)


def scan_text(text: str) -> list[dict]:
    findings: list[dict] = []
    for rule_id, pat in RULES:
        for m in pat.finditer(text):
            hit = m.group(0)
            if is_placeholder(hit) or is_placeholder(text[max(0, m.start() - 60):m.end() + 20]):
                continue
            line = text.count("\n", 0, m.start()) + 1
            findings.append({"rule": rule_id, "match": hit[:80], "line": line})
    return findings


def list_rules() -> list[str]:
    return [r[0] for r in RULES]


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--list-rules" in argv:
        print("\n".join(list_rules()))
        return 0
    text = sys.stdin.read() if not [a for a in argv if not a.startswith("-")] else Path(argv[0]).read_text(encoding="utf-8", errors="ignore")
    findings = scan_text(text)
    for f in findings:
        print(f"[{f['rule']}] line {f['line']}: {f['match']}")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
