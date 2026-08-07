# -*- coding: utf-8 -*-
"""战略分析师数据库 - 检索问答入口
用法: python ask.py "我的问题"
     python ask.py "该不该负债扩张" --top 5 --show 3
"""
import json, re, sys, argparse
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent  # 仓库根目录（支持任意位置 clone 运行）

# ---------- BM25 ----------
class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.docs = docs
        self.k1, self.b = k1, b
        self.N = len(docs)
        self.avgdl = sum(len(d) for d in docs) / max(self.N, 1)
        self.df = Counter()
        for d in docs:
            for t in set(d):
                self.df[t] += 1
        self.idf = {t: __import__('math').log(1 + (self.N - f + 0.5) / (f + 0.5)) for t, f in self.df.items()}

    def score(self, q, d):
        dl = len(d)
        if dl == 0: return 0.0
        c = Counter(d)
        s = 0.0
        for t in set(q):
            if t not in self.idf: continue
            tf = c.get(t, 0)
            s += self.idf[t] * tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
        return s

    def search(self, q, top=10):
        scored = [(self.score(q, d), i) for i, d in enumerate(self.docs)]
        scored.sort(reverse=True)
        return scored[:top]

# ---------- 数据加载 ----------
def tokenize(t):
    t = t.lower()
    t = re.sub(r'[^\u4e00-\u9fff0-9a-zA-Z]', ' ', t)
    # 中文按字切分（2-gram 兼顾召回与精度）
    tokens = []
    for seg in re.findall(r'[\u4e00-\u9fff]+|[0-9a-zA-Z]+', t):
        if re.match(r'[\u4e00-\u9fff]+$', seg):
            if len(seg) == 1:
                tokens.append(seg)
            else:
                tokens.extend(seg[i:i+2] for i in range(len(seg)-1))
                tokens.append(seg)
        else:
            tokens.append(seg)
    return tokens

def load_corpus():
    """加载 L0 播客 + 书 + L1 原子层(若存在)"""
    entries = []
    # 播客每期切块（按 ~800 字，保留期号引用）
    pod = ROOT / '财富自由之路_全量.jsonl'
    if pod.exists():
        for line in pod.read_text(encoding='utf-8').splitlines():
            r = json.loads(line)
            text = r.get('clean_text') or r['text']
            chunks = [text[i:i+800] for i in range(0, len(text), 800)]
            for ci, c in enumerate(chunks):
                entries.append({
                    'text': c, 'kind': '播客',
                    'source': f"ep{r['episode']} {r['title']}",
                    'url': r.get('source_url',''), 'chunk': ci,
                })
    # 书
    bk = ROOT / '书_这世界既残酷也温柔.jsonl'
    if bk.exists():
        for line in bk.read_text(encoding='utf-8').splitlines():
            r = json.loads(line)
            text = r.get('text','')
            if len(text) < 100: continue
            if r['chapter'] in ('封面','Table of Contents') or r['chapter'].startswith('PART'): continue
            chunks = [text[i:i+800] for i in range(0, len(text), 800)]
            for ci, c in enumerate(chunks):
                entries.append({
                    'text': c, 'kind': '书',
                    'source': f"书:{r['chapter']}",
                    'url': '', 'chunk': ci,
                })
    # L1 原子层（若已生成）：每条作为独立高权重条目
    at = ROOT / 'atoms.jsonl'
    if at.exists():
        for line in at.read_text(encoding='utf-8').splitlines():
            r = json.loads(line)
            txt = f"{r.get('claim','')} {r.get('detail','')} {r.get('evidence','')} {' '.join(r.get('tags',[]))}"
            entries.append({
                'text': txt, 'kind': 'L1原子',
                'source': f"L1:{r.get('source','')}",
                'url': '', 'chunk': 0,
            })
    # 后期访谈层（2025-2026 转录，自动加载 访谈_*.jsonl）
    for f in sorted(ROOT.glob('访谈_*.jsonl')):
        for line in f.read_text(encoding='utf-8').splitlines():
            r = json.loads(line)
            text = r.get('text','')
            if not text: continue
            entries.append({
                'text': text, 'kind': '访谈',
                'source': f"访谈:{r['source']} [{r.get('start','')}]",
                'url': '', 'chunk': 0,
            })
    return entries

# ---------- 主流程 ----------
def main():
    ap = argparse.ArgumentParser(description='孙宇晨战略数据库检索')
    ap.add_argument('query', help='你的问题')
    ap.add_argument('--top', type=int, default=6, help='返回结果数')
    ap.add_argument('--show', type=int, default=2, help='每个来源展示片段数')
    ap.add_argument('--l1', action='store_true', help='优先检索 L1 原子层')
    args = ap.parse_args()

    entries = load_corpus()
    if not entries:
        print('未找到数据文件'); return
    docs = [tokenize(e['text']) for e in entries]
    bm = BM25(docs)
    q = tokenize(args.query)
    hits = bm.search(q, top=args.top*3)

    # 按来源聚合，取每个来源 top 片段
    from collections import defaultdict
    by_src = defaultdict(list)
    for score, i in hits:
        by_src[entries[i]['source']].append((score, entries[i]))
    print(f'=== 命中 {len(hits)} 个片段 / {len(by_src)} 个来源 ===\n')
    shown = 0
    for src, items in sorted(by_src.items(), key=lambda x: -max(s for s,_ in x[1]))[:args.top]:
        items.sort(key=lambda x: -x[0])
        e = items[0][1]
        print(f'▶ {e["kind"]} | {src}')
        if e['url']: print(f'  来源: {e["url"]}')
        snippet = items[0][0] if items[0][1]['chunk'] > 0 else e['text']
        print(f'  {e["text"][:220].replace(chr(10)," ")}')
        print()
        shown += 1
    print(f'(共 {shown} 个来源，可加 --top N 调整)')

if __name__ == '__main__':
    main()
