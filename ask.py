# -*- coding: utf-8 -*-
"""孙宇晨战略分析师：可追溯证据检索入口。"""

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EARLY_PERIOD = "2016-2017"


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.docs = docs
        self.k1, self.b = k1, b
        self.total = len(docs)
        self.avgdl = sum(len(doc) for doc in docs) / max(self.total, 1)
        self.df = Counter()
        for doc in docs:
            for token in set(doc):
                self.df[token] += 1
        self.idf = {
            token: math.log(1 + (self.total - freq + 0.5) / (freq + 0.5))
            for token, freq in self.df.items()
        }

    def score(self, query_tokens, doc_tokens):
        if not doc_tokens:
            return 0.0
        counts = Counter(doc_tokens)
        score = 0.0
        for token in set(query_tokens):
            if token not in self.idf:
                continue
            frequency = counts.get(token, 0)
            denominator = frequency + self.k1 * (
                1 - self.b + self.b * len(doc_tokens) / self.avgdl
            )
            score += self.idf[token] * frequency * (self.k1 + 1) / denominator
        return score



def tokenize(text):
    text = text.lower()
    text = re.sub(r"[^\u4e00-\u9fff0-9a-zA-Z]", " ", text)
    tokens = []
    for segment in re.findall(r"[\u4e00-\u9fff]+|[0-9a-zA-Z]+", text):
        if re.fullmatch(r"[\u4e00-\u9fff]+", segment):
            if len(segment) == 1:
                tokens.append(segment)
            else:
                tokens.extend(segment[index : index + 2] for index in range(len(segment) - 1))
                tokens.append(segment)
        else:
            tokens.append(segment)
    return tokens



def read_jsonl(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]



def load_scenario_map():
    scenario_map = defaultdict(list)
    for row in read_jsonl(ROOT / "scenarios.jsonl"):
        for atom_id in row.get("atom_ids", []):
            if row["scenario"] not in scenario_map[atom_id]:
                scenario_map[atom_id].append(row["scenario"])
    return scenario_map



def base_entry(**values):
    entry = {
        "id": "",
        "kind": "",
        "source": "",
        "source_period": "",
        "summary": "",
        "detail": "",
        "quote": "",
        "url": "",
        "scenarios": [],
        "search_text": "",
    }
    entry.update(values)
    return entry



def load_corpus():
    entries = []
    scenario_map = load_scenario_map()

    for row in read_jsonl(ROOT / "财富自由之路_全量.jsonl"):
        text = row.get("clean_text") or row.get("text", "")
        for chunk_index, chunk in enumerate(text[index : index + 800] for index in range(0, len(text), 800)):
            entries.append(
                base_entry(
                    id=f"podcast-{row['episode']}-{chunk_index}",
                    kind="播客",
                    source=f"ep{row['episode']} {row['title']}",
                    source_period=EARLY_PERIOD,
                    quote=chunk,
                    url=row.get("source_url", ""),
                    search_text=chunk,
                )
            )

    for row in read_jsonl(ROOT / "书_这世界既残酷也温柔.jsonl"):
        text = row.get("text", "")
        chapter = row.get("chapter", "")
        if len(text) < 100 or chapter in ("封面", "Table of Contents") or chapter.startswith("PART"):
            continue
        for chunk_index, chunk in enumerate(text[index : index + 800] for index in range(0, len(text), 800)):
            entries.append(
                base_entry(
                    id=f"book-{chapter}-{chunk_index}",
                    kind="书",
                    source=f"书:{chapter}",
                    source_period="2017",
                    quote=chunk,
                    search_text=chunk,
                )
            )

    for row in read_jsonl(ROOT / "atoms.jsonl"):
        scenarios = scenario_map.get(row.get("id", ""), [])
        summary = row.get("claim", "")
        detail = row.get("detail", "")
        quote = row.get("evidence", "")
        tags = row.get("tags", [])
        actionable = row.get("actionable", "")
        search_text = " ".join(
            [summary, detail, quote, " ".join(tags), actionable, " ".join(scenarios)]
        )
        entries.append(
            base_entry(
                id=row.get("id", ""),
                kind="L1原子",
                source=row.get("source", ""),
                source_period=EARLY_PERIOD,
                summary=summary,
                detail=detail,
                quote=quote,
                scenarios=scenarios,
                search_text=search_text,
            )
        )

    for path in sorted(ROOT.glob("访谈_*.jsonl")):
        for row in read_jsonl(path):
            text = row.get("text", "")
            if not text:
                continue
            date = str(row.get("date", ""))
            year_match = re.search(r"20\d{2}", date or row.get("source", ""))
            period = year_match.group(0) if year_match else "未标注"
            entries.append(
                base_entry(
                    id=row.get("id", ""),
                    kind="访谈",
                    source=f"访谈:{row.get('source', path.stem)} [{row.get('start', '')}]",
                    source_period=period,
                    quote=text,
                    search_text=" ".join([row.get("note", ""), text]),
                )
            )

    return entries



def public_result(entry, score):
    return {
        "id": entry["id"],
        "kind": entry["kind"],
        "source": entry["source"],
        "source_period": entry["source_period"],
        "summary": entry["summary"],
        "detail": entry["detail"],
        "quote": entry["quote"],
        "url": entry["url"],
        "scenarios": entry["scenarios"],
        "score": round(score, 6),
    }



def search_corpus(query, top=6, l1_only=False):
    entries = load_corpus()
    if l1_only:
        entries = [entry for entry in entries if entry["kind"] == "L1原子"]
    if not entries or not query.strip() or top <= 0:
        return []

    docs = [tokenize(entry["search_text"]) for entry in entries]
    query_tokens = tokenize(query)
    if not query_tokens:
        return []
    index = BM25(docs)
    scored = []
    for position, doc in enumerate(docs):
        score = index.score(query_tokens, doc)
        if score <= 0:
            continue
        if entries[position]["kind"] == "L1原子" and not l1_only:
            score *= 1.15
        scored.append((score, position))
    scored.sort(reverse=True)

    results = []
    per_source = Counter()
    for score, position in scored:
        entry = entries[position]
        if per_source[entry["source"]] >= 2:
            continue
        results.append(public_result(entry, score))
        per_source[entry["source"]] += 1
        if len(results) >= top:
            break
    return results



def print_human(query, results):
    if not results:
        print(f'没有找到与“{query}”直接相关的证据。')
        return
    print(f"=== {len(results)} 条可追溯证据 ===\n")
    for item in results:
        print(f"▶ {item['kind']} | {item['source']} | {item['source_period']}")
        if item["scenarios"]:
            print(f"  场景: {' / '.join(item['scenarios'])}")
        if item["summary"]:
            print(f"  摘要（提炼，不是原话）: {item['summary']}")
        if item["quote"]:
            quote = item["quote"][:260].replace("\n", " ")
            print(f"  原文: {quote}")
        if item["url"]:
            print(f"  来源: {item['url']}")
        print()



def main():
    parser = argparse.ArgumentParser(description="检索孙宇晨公开表达中的可追溯证据")
    parser.add_argument("query", help="需要分析的问题")
    parser.add_argument("--top", type=int, default=8, help="返回证据条数")
    parser.add_argument("--l1", "--l1-only", dest="l1_only", action="store_true", help="只检索提炼观点")
    parser.add_argument("--json", action="store_true", help="输出适合 Agent 读取的 JSON")
    args = parser.parse_args()

    results = search_corpus(args.query, top=args.top, l1_only=args.l1_only)
    if args.json:
        payload = {
            "query": args.query,
            "result_count": len(results),
            "results": results,
            "rules": {
                "summary_is_not_quote": True,
                "quote_must_be_verified_in_source": True,
                "do_not_mix_periods": True,
            },
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_human(args.query, results)


if __name__ == "__main__":
    main()
