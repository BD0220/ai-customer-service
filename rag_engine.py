"""
RAG 检索增强模块
将知识库文档分块索引，根据用户问题检索最相关的段落。
使用轻量级 TF 相似度实现，无需额外依赖。
"""

import os
import re
import math
from collections import Counter

# 知识库目录
KB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_base")


def _tokenize(text: str) -> list[str]:
    """
    简易中文分词：按标点和空格切分，对中文按 2-gram 提取。
    生产环境应替换为 jieba 等专业分词库。
    """
    # 清理 markdown 符号
    text = re.sub(r'[#*`>\-\[\]()]', ' ', text)
    # 提取中文词组（2字以上）和英文单词
    tokens = []
    # 英文单词
    tokens.extend(re.findall(r'[a-zA-Z0-9]+', text.lower()))
    # 中文 2-gram
    chinese_chars = re.findall(r'[\u4e00-\u9fff]+', text)
    for seg in chinese_chars:
        for i in range(len(seg) - 1):
            tokens.append(seg[i:i+2])
        if len(seg) == 1:
            tokens.append(seg)
    return tokens


def _split_into_chunks(text: str, source: str, max_chars: int = 200) -> list[dict]:
    """
    将文档按段落分块，每个块不超过 max_chars 字符。
    保留标题层级作为上下文。
    """
    chunks = []
    current_h1 = ""
    current_h2 = ""
    buffer = ""

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        # 追踪标题
        if line.startswith("# "):
            current_h1 = line[2:].strip()
            current_h2 = ""
            continue
        elif line.startswith("## "):
            # 保存之前的 buffer
            if buffer.strip():
                chunks.append({
                    "content": buffer.strip(),
                    "source": source,
                    "section": f"{current_h1} > {current_h2}" if current_h2 else current_h1,
                })
                buffer = ""
            current_h2 = line[3:].strip()
            continue
        elif line.startswith("### "):
            if buffer.strip():
                chunks.append({
                    "content": buffer.strip(),
                    "source": source,
                    "section": f"{current_h1} > {current_h2}",
                })
                buffer = ""
            current_h2 = (current_h2 + " > " if current_h2 else "") + line[4:].strip()
            continue

        # 累积内容行
        if len(buffer) + len(line) > max_chars and buffer:
            chunks.append({
                "content": buffer.strip(),
                "source": source,
                "section": f"{current_h1} > {current_h2}" if current_h2 else current_h1,
            })
            buffer = line
        else:
            buffer = buffer + "\n" + line if buffer else line

    # 最后一个块
    if buffer.strip():
        chunks.append({
            "content": buffer.strip(),
            "source": source,
            "section": f"{current_h1} > {current_h2}" if current_h2 else current_h1,
        })

    return chunks


def _build_index():
    """扫描知识库目录，构建检索索引"""
    chunks = []
    for filename in os.listdir(KB_DIR):
        if not filename.endswith(".md"):
            continue
        filepath = os.path.join(KB_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        doc_chunks = _split_into_chunks(content, filename)
        chunks.extend(doc_chunks)

    # 预计算每个块的词频和文档频率
    index = []
    doc_freq = Counter()
    for chunk in chunks:
        tokens = _tokenize(chunk["content"])
        tf = Counter(tokens)
        index.append({
            **chunk,
            "tokens": tokens,
            "tf": tf,
            "length": len(tokens),
        })
        for term in tf.keys():
            doc_freq[term] += 1

    total_docs = len(index)
    # 计算 IDF
    idf = {}
    for term, df in doc_freq.items():
        idf[term] = math.log((total_docs + 1) / (df + 1)) + 1

    return index, idf, total_docs


def _tfidf_score(query_tokens: list[str], chunk: dict, idf: dict) -> float:
    """计算查询和文档块的 TF-IDF 余弦相似度"""
    if chunk["length"] == 0:
        return 0.0

    query_tf = Counter(query_tokens)
    score = 0.0
    for term, qtf in query_tf.items():
        if term in chunk["tf"]:
            q_weight = qtf * idf.get(term, 1.0)
            d_weight = chunk["tf"][term] * idf.get(term, 1.0)
            score += q_weight * d_weight

    # 归一化
    query_norm = math.sqrt(sum(
        (qtf * idf.get(term, 1.0)) ** 2 for term, qtf in query_tf.items()
    ))
    doc_norm = math.sqrt(sum(
        (chunk["tf"][term] * idf.get(term, 1.0)) ** 2 for term in chunk["tf"]
    ))

    if query_norm > 0 and doc_norm > 0:
        score = score / (query_norm * doc_norm)
    return score


def search_knowledge_base(query: str, top_k: int = 3) -> list[dict]:
    """
    检索知识库中与查询最相关的段落。

    Args:
        query: 用户问题
        top_k: 返回最相关的前 K 条

    Returns:
        相关段落列表，每条包含 content、source、section、score
    """
    index, idf, total_docs = _build_index()

    if total_docs == 0:
        return []

    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    # 计算所有块的得分
    scored = []
    for chunk in index:
        score = _tfidf_score(query_tokens, chunk, idf)
        if score > 0:
            scored.append({
                "content": chunk["content"],
                "source": chunk["source"],
                "section": chunk["section"],
                "score": round(score, 4),
            })

    # 按得分排序，取 top_k
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def format_context(results: list[dict]) -> str:
    """
    将检索结果格式化为注入 System Prompt 的上下文字符串。
    """
    if not results:
        return ""

    parts = []
    for i, r in enumerate(results, 1):
        parts.append(
            f"【参考资料 {i}】（来源：{r['source']} > {r['section']}）\n{r['content']}"
        )
    return "\n\n".join(parts)


if __name__ == "__main__":
    # 测试检索
    test_queries = [
        "退货需要什么条件？",
        "退款多久能到账？",
        "耳机保修多久？",
        "怎么开发票？",
    ]
    for q in test_queries:
        print(f"\n{'='*60}")
        print(f"问题：{q}")
        results = search_knowledge_base(q, top_k=2)
        for r in results:
            print(f"  [score={r['score']}] {r['section']}")
            print(f"  {r['content'][:100]}...")
