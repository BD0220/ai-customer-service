"""
RAG 检索引擎模块
提供统一的检索器抽象接口，当前内置 TF-IDF 检索实现，可平滑切换到 Embedding 向量检索。

使用方式：
    retriever = get_retriever()              # 默认 TF-IDF
    results = retriever.search("退货政策")   # 返回 Top-K 相关段落
    context = retriever.format_context(results)

扩展新检索方式：
    1. 继承 BaseRetriever
    2. 实现 search() 和 format_context()
    3. 在 RETRIEVER_REGISTRY 中注册
    4. 设置环境变量 RAG_RETRIEVER=your_retriever
"""

import os
import re
import math
import logging
from abc import ABC, abstractmethod
from collections import Counter

logger = logging.getLogger(__name__)

# 知识库目录
KB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_base")


# ========== 抽象基类 ==========

class BaseRetriever(ABC):
    """检索器抽象基类，所有检索方案必须实现 search 和 format_context。"""

    @abstractmethod
    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """
        检索与查询最相关的文档段落。

        Args:
            query: 用户问题
            top_k: 返回前 K 条结果

        Returns:
            结果列表，每条包含 content、source、section、score
        """
        pass

    @abstractmethod
    def format_context(self, results: list[dict]) -> str:
        """将检索结果格式化为注入 Prompt 的上下文字符串。"""
        pass


# ========== 文档分块（通用工具） ==========

def split_into_chunks(text: str, source: str, max_chars: int = 200) -> list[dict]:
    """
    将文档按标题层级分块，每个块不超过 max_chars 字符。
    保留章节层级作为上下文。
    """
    chunks = []
    current_h1 = ""
    current_h2 = ""
    buffer = ""

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        if line.startswith("# "):
            current_h1 = line[2:].strip()
            current_h2 = ""
            continue
        elif line.startswith("## "):
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

        if len(buffer) + len(line) > max_chars and buffer:
            chunks.append({
                "content": buffer.strip(),
                "source": source,
                "section": f"{current_h1} > {current_h2}" if current_h2 else current_h1,
            })
            buffer = line
        else:
            buffer = buffer + "\n" + line if buffer else line

    if buffer.strip():
        chunks.append({
            "content": buffer.strip(),
            "source": source,
            "section": f"{current_h1} > {current_h2}" if current_h2 else current_h1,
        })

    return chunks


def _load_all_chunks() -> list[dict]:
    """扫描知识库目录，加载所有文档并分块。"""
    chunks = []
    if not os.path.isdir(KB_DIR):
        logger.warning(f"知识库目录不存在：{KB_DIR}")
        return chunks
    for filename in os.listdir(KB_DIR):
        if not filename.endswith(".md"):
            continue
        filepath = os.path.join(KB_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        chunks.extend(split_into_chunks(content, filename))
    return chunks


# ========== TF-IDF 检索实现 ==========

def _tokenize(text: str) -> list[str]:
    """
    简易中文分词：按标点切分，对中文按 2-gram 提取。
    生产环境可替换为 jieba 等专业分词库。
    """
    text = re.sub(r'[#*`>\-\[\]()]', ' ', text)
    tokens = []
    tokens.extend(re.findall(r'[a-zA-Z0-9]+', text.lower()))
    chinese_chars = re.findall(r'[\u4e00-\u9fff]+', text)
    for seg in chinese_chars:
        for i in range(len(seg) - 1):
            tokens.append(seg[i:i+2])
        if len(seg) == 1:
            tokens.append(seg)
    return tokens


class TfidfRetriever(BaseRetriever):
    """基于 TF-IDF + 余弦相似度的轻量检索器，零外部依赖。"""

    def __init__(self):
        self._build_index()

    def _build_index(self):
        """构建 TF-IDF 索引。"""
        chunks = _load_all_chunks()
        self.index = []
        doc_freq = Counter()
        for chunk in chunks:
            tokens = _tokenize(chunk["content"])
            tf = Counter(tokens)
            self.index.append({
                **chunk,
                "tokens": tokens,
                "tf": tf,
                "length": len(tokens),
            })
            for term in tf.keys():
                doc_freq[term] += 1

        total_docs = len(self.index)
        self.idf = {}
        for term, df in doc_freq.items():
            self.idf[term] = math.log((total_docs + 1) / (df + 1)) + 1
        logger.info(f"TF-IDF 索引构建完成，共 {total_docs} 个文档块")

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        if not self.index:
            return []
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scored = []
        for chunk in self.index:
            score = self._cosine_score(query_tokens, chunk)
            if score > 0:
                scored.append({
                    "content": chunk["content"],
                    "source": chunk["source"],
                    "section": chunk["section"],
                    "score": round(score, 4),
                })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def _cosine_score(self, query_tokens: list[str], chunk: dict) -> float:
        """计算 TF-IDF 余弦相似度。"""
        if chunk["length"] == 0:
            return 0.0
        query_tf = Counter(query_tokens)
        score = 0.0
        for term, qtf in query_tf.items():
            if term in chunk["tf"]:
                q_weight = qtf * self.idf.get(term, 1.0)
                d_weight = chunk["tf"][term] * self.idf.get(term, 1.0)
                score += q_weight * d_weight

        query_norm = math.sqrt(
            sum((qtf * self.idf.get(term, 1.0)) ** 2 for term, qtf in query_tf.items())
        )
        doc_norm = math.sqrt(
            sum((chunk["tf"][t] * self.idf.get(t, 1.0)) ** 2 for t in chunk["tf"])
        )
        if query_norm > 0 and doc_norm > 0:
            score = score / (query_norm * doc_norm)
        return score

    def format_context(self, results: list[dict]) -> str:
        if not results:
            return ""
        parts = []
        for i, r in enumerate(results, 1):
            parts.append(
                f"【参考资料 {i}】（来源：{r['source']} > {r['section']}）\n{r['content']}"
            )
        return "\n\n".join(parts)


# ========== Embedding 向量检索接口（预留扩展） ==========

class EmbeddingRetriever(BaseRetriever):
    """
    基于 Embedding 的向量检索器骨架。
    生产环境可接入 OpenAI Embeddings / Chroma / Milvus 等，
    实现 search 方法即可无缝替换 TF-IDF 检索器。

    示例用法（接入 Chroma）：
        retriever = EmbeddingRetriever(
            embedding_model="text-embedding-3-small",
            vector_db_path="./chroma_db"
        )
    """

    def __init__(self, embedding_model: str = None, vector_db_path: str = None):
        self.embedding_model = embedding_model or os.getenv(
            "EMBEDDING_MODEL", "text-embedding-3-small"
        )
        self.vector_db_path = vector_db_path or os.getenv(
            "VECTOR_DB_PATH", "./vector_db"
        )
        self._client = None
        logger.info(
            f"EmbeddingRetriever 已配置（模型：{self.embedding_model}，"
            f"向量库路径：{self.vector_db_path}）。"
            "如需启用，请安装 chromadb 并实现向量索引逻辑。"
        )

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        # TODO: 接入 Embedding 模型和向量数据库后实现
        # 1. 调用 embedding 模型将 query 转向量
        # 2. 在向量库中 ANN 检索 top_k
        # 3. 返回标准化结果
        logger.warning("EmbeddingRetriever.search() 尚未实现，请接入向量数据库后使用")
        return []

    def format_context(self, results: list[dict]) -> str:
        if not results:
            return ""
        parts = []
        for i, r in enumerate(results, 1):
            parts.append(
                f"【参考资料 {i}】（来源：{r['source']} > {r['section']}）\n{r['content']}"
            )
        return "\n\n".join(parts)


# ========== 工厂函数 ==========

RETRIEVER_REGISTRY = {
    "tfidf": TfidfRetriever,
    "embedding": EmbeddingRetriever,
}


def get_retriever(retriever_name: str = None) -> BaseRetriever:
    """
    工厂函数：根据配置返回检索器实例。

    Args:
        retriever_name: 检索器名称，不传则从 RAG_RETRIEVER 环境变量读取（默认 tfidf）

    Returns:
        BaseRetriever 实例
    """
    name = (retriever_name or os.getenv("RAG_RETRIEVER", "tfidf")).lower()
    retriever_cls = RETRIEVER_REGISTRY.get(name)
    if not retriever_cls:
        raise ValueError(
            f"未知的检索器：{name}，当前支持：{', '.join(RETRIEVER_REGISTRY.keys())}"
        )
    return retriever_cls()


# ========== 向后兼容的便捷函数 ==========
# 保持原有 API 不变，customer_service_agent.py 无需改动即可使用

_default_retriever = None


def _get_default():
    global _default_retriever
    if _default_retriever is None:
        _default_retriever = get_retriever()
    return _default_retriever


def search_knowledge_base(query: str, top_k: int = 3) -> list[dict]:
    """检索知识库（向后兼容接口）。"""
    return _get_default().search(query, top_k)


def format_context(results: list[dict]) -> str:
    """格式化检索结果（向后兼容接口）。"""
    return _get_default().format_context(results)


if __name__ == "__main__":
    # 测试检索
    logging.basicConfig(level=logging.INFO)
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
