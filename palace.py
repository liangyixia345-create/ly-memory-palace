"""
LY Memory Palace — 类人脑分层记忆系统 (CLI 版)
=============================================
Author: liangyi
Version: 1.0.0
License: MIT

纯 CLI 工具，AI 通过 exec 调用实现跨会话长期记忆。

核心机制：
- 三层记忆：语义记忆(事实) / 情景记忆(事件) / 程序记忆(习惯)
- 海马体索引：关键词→记忆的关联映射，实现被动唤醒
- 艾宾浩斯遗忘曲线：记忆强度随时间衰减，被使用时强化
- 关联网络：记忆之间可建立连接，唤醒一个会激活相关记忆

用法：
  python palace.py recall "用户的消息"
  python palace.py store --layer semantic --keywords "k1,k2" --content "内容"
  python palace.py list [--layer semantic|episodic|procedural] [--sort strength|recent|created]
  python palace.py stats
  python palace.py remove --id <memory_id>
  python palace.py decay
  python palace.py export [--file backup.json]
  python palace.py import --file backup.json
"""

__author__ = "liangyi"
__version__ = "1.0.0"

import json
import time
import math
import re
import os
import sys
import hashlib
import argparse
import io
from pathlib import Path
from collections import defaultdict

# 修复 Windows 控制台 UTF-8 输出
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── 配置 ──
SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
DATA_DIR = SCRIPT_DIR / "data"


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


CFG = load_config()
SETTINGS = CFG.get("settings", {})
LAYERS = CFG.get("memory_layers", {})


# ══════════════════════════════════════
#  数据结构
# ══════════════════════════════════════

class MemoryItem:
    """一条记忆"""

    def __init__(self, data=None):
        if data:
            self.__dict__.update(data)
        else:
            self.id = ""
            self.layer = "semantic"
            self.content = ""
            self.keywords = []
            self.associations = []
            self.strength = 0.8
            self.access_count = 0
            self.last_accessed = 0
            self.created = 0
            self.source = ""
            self.context = ""
            self.scope = "global"
            self.tags = []
            self.emotion = "neutral"

    def to_dict(self):
        return self.__dict__.copy()

    def effective_strength(self):
        """计算当前有效强度（考虑艾宾浩斯时间衰减）"""
        if self.strength <= 0:
            return 0
        now = time.time()
        hours_since = (now - self.last_accessed) / 3600
        if hours_since <= 0:
            return self.strength

        layer_cfg = LAYERS.get(self.layer, {})
        decay_mult = layer_cfg.get("decay_multiplier", 1.0)
        decay_rate = SETTINGS.get("decay_rate", 0.05)

        # 艾宾浩斯遗忘曲线: R = e^(-t/S)
        stability = max(1, self.access_count * 2 + self.strength * 10)
        decay = math.exp(-(hours_since * decay_rate * decay_mult) / stability)

        return self.strength * decay


# ══════════════════════════════════════
#  记忆宫殿引擎
# ══════════════════════════════════════

class MemoryPalace:
    """记忆宫殿主引擎"""

    # 中文停用词
    _STOP_WORDS = set("的了是在我你他她它们这那个有和与或但如果因为所以就也都还要会能可以被把将从到对于又不没无很太最")
    # 英文停用词
    _STOP_WORDS_EN = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "can", "shall", "to", "of", "in", "for",
        "on", "with", "at", "by", "from", "as", "into", "about", "like",
        "through", "after", "before", "between", "under", "above", "up",
        "down", "out", "off", "over", "and", "or", "but", "not", "no", "so",
        "if", "then", "than", "too", "very", "just", "that", "this", "it", "i",
        "you", "he", "she", "they", "we", "me", "him", "her", "them", "us",
        "my", "your", "his", "its", "our", "their", "what", "which", "who",
        "how", "when", "where", "why"
    }

    def __init__(self, storage_dir=None):
        self.storage_dir = Path(storage_dir) if storage_dir else DATA_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.memories_file = self.storage_dir / "memories.json"
        self.index_file = self.storage_dir / "hippocampus_index.json"
        self._memories = {}
        self._keyword_index = {}
        self._load()

    # ── 持久化 ──

    def _load(self):
        if self.memories_file.exists():
            try:
                with open(self.memories_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item_data in data:
                    mi = MemoryItem(item_data)
                    self._memories[mi.id] = mi
            except Exception:
                self._memories = {}

        if self.index_file.exists():
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    self._keyword_index = json.load(f)
            except Exception:
                self._keyword_index = {}
        else:
            self._rebuild_index()

    def _save(self):
        data = [m.to_dict() for m in self._memories.values()]
        with open(self.memories_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self._keyword_index, f, ensure_ascii=False, indent=2)

    def _rebuild_index(self):
        self._keyword_index = {}
        for mid, mem in self._memories.items():
            for kw in mem.keywords:
                kw_lower = kw.lower()
                if kw_lower not in self._keyword_index:
                    self._keyword_index[kw_lower] = []
                if mid not in self._keyword_index[kw_lower]:
                    self._keyword_index[kw_lower].append(mid)

    # ── 关键词提取 ──

    def _extract_keywords(self, text):
        if not text:
            return []
        keywords = []

        # 英文词
        en_words = re.findall(r'[a-zA-Z][a-zA-Z0-9_]{1,}', text)
        for w in en_words:
            if w.lower() not in self._STOP_WORDS_EN and len(w) > 1:
                keywords.append(w.lower())

        # 中文词组（2-4字滑动窗口）
        cn_text = re.sub(r'[a-zA-Z0-9\s_\-\.\,\!\?\;\:\'\"\(\)\[\]\{\}]', ' ', text)
        cn_chars = re.findall(r'[\u4e00-\u9fff]+', cn_text)
        for seg in cn_chars:
            for length in [4, 3, 2]:
                for i in range(len(seg) - length + 1):
                    chunk = seg[i:i + length]
                    if not all(c in self._STOP_WORDS for c in chunk):
                        keywords.append(chunk)
            if len(seg) >= 2 and seg not in keywords:
                keywords.append(seg)

        seen = set()
        unique = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique.append(kw)
        return unique[:20]

    # ── 记忆存储 ──

    def store(self, content, layer="semantic", keywords=None, tags=None,
              source="", context="", scope="global", emotion="neutral",
              associations=None):
        now = time.time()
        mid = hashlib.md5(f"{content}{now}".encode()).hexdigest()[:12]

        if not keywords:
            keywords = self._extract_keywords(content)

        layer_cfg = LAYERS.get(layer, {})
        base_strength = layer_cfg.get("base_strength", 0.7)

        # 重复检测
        dup = self._find_duplicate(content, keywords)
        if dup:
            self._reinforce(dup.id)
            for kw in keywords:
                if kw not in dup.keywords:
                    dup.keywords.append(kw)
            if context and not dup.context:
                dup.context = context
            self._rebuild_index()
            self._save()
            return dup.id, True  # (id, was_duplicate)

        mi = MemoryItem()
        mi.id = mid
        mi.layer = layer
        mi.content = content
        mi.keywords = keywords
        mi.associations = associations or []
        mi.strength = base_strength
        mi.access_count = 0
        mi.last_accessed = now
        mi.created = now
        mi.source = source
        mi.context = context
        mi.scope = scope
        mi.tags = tags or []
        mi.emotion = emotion

        self._memories[mid] = mi

        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower not in self._keyword_index:
                self._keyword_index[kw_lower] = []
            self._keyword_index[kw_lower].append(mid)

        self._auto_associate(mid)
        self._enforce_limits()
        self._save()
        return mid, False

    def _find_duplicate(self, content, keywords):
        content_lower = content.lower()
        for mem in self._memories.values():
            if mem.content.lower() == content_lower:
                return mem
            if keywords and mem.keywords:
                overlap = len(set(k.lower() for k in keywords) & set(k.lower() for k in mem.keywords))
                if overlap >= 2 and (content_lower in mem.content.lower() or mem.content.lower() in content_lower):
                    return mem
        return None

    def _auto_associate(self, mid):
        mem = self._memories[mid]
        related_ids = set()
        for kw in mem.keywords:
            kw_lower = kw.lower()
            if kw_lower in self._keyword_index:
                for related_id in self._keyword_index[kw_lower]:
                    if related_id != mid:
                        related_ids.add(related_id)
        for rid in related_ids:
            if rid not in mem.associations:
                mem.associations.append(rid)
            related_mem = self._memories.get(rid)
            if related_mem and mid not in related_mem.associations:
                related_mem.associations.append(mid)

    def _enforce_limits(self):
        max_semantic = SETTINGS.get("max_semantic_memories", 200)
        max_episodic = SETTINGS.get("max_episodic_memories", 100)
        max_procedural = SETTINGS.get("max_procedural_memories", 150)
        forget_threshold = SETTINGS.get("forget_threshold", 0.05)

        to_remove = [mid for mid, mem in self._memories.items()
                     if mem.effective_strength() < forget_threshold]
        for mid in to_remove:
            self._forget(mid)

        limits = {"semantic": max_semantic, "episodic": max_episodic, "procedural": max_procedural}
        for layer, max_count in limits.items():
            layer_mems = [(mid, m) for mid, m in self._memories.items() if m.layer == layer]
            if len(layer_mems) > max_count:
                layer_mems.sort(key=lambda x: x[1].effective_strength())
                for mid, _ in layer_mems[:len(layer_mems) - max_count]:
                    self._forget(mid)

    def _forget(self, mid):
        mem = self._memories.get(mid)
        if not mem:
            return
        for kw in mem.keywords:
            kw_lower = kw.lower()
            if kw_lower in self._keyword_index:
                self._keyword_index[kw_lower] = [i for i in self._keyword_index[kw_lower] if i != mid]
                if not self._keyword_index[kw_lower]:
                    del self._keyword_index[kw_lower]
        for rid in mem.associations:
            related = self._memories.get(rid)
            if related:
                related.associations = [a for a in related.associations if a != mid]
        del self._memories[mid]

    def _reinforce(self, mid):
        mem = self._memories.get(mid)
        if not mem:
            return
        boost = SETTINGS.get("reinforce_boost", 0.3)
        mem.strength = min(1.0, mem.strength + boost * (1 - mem.strength))
        mem.access_count += 1
        mem.last_accessed = time.time()

    # ── 关联唤醒 ──

    def recall(self, query, max_results=None, min_strength=None):
        if max_results is None:
            max_results = SETTINGS.get("max_context_inject", 15)
        if min_strength is None:
            min_strength = SETTINGS.get("activation_threshold", 0.2)

        query_keywords = self._extract_keywords(query)
        query_lower = query.lower()

        # 第一层：关键词匹配
        activated = {}
        for kw in query_keywords:
            kw_lower = kw.lower()
            if kw_lower in self._keyword_index:
                for mid in self._keyword_index[kw_lower]:
                    activated[mid] = activated.get(mid, 0) + 1.0
            for idx_kw, mids in self._keyword_index.items():
                if idx_kw != kw_lower and (kw_lower in idx_kw or idx_kw in kw_lower):
                    for mid in mids:
                        activated[mid] = activated.get(mid, 0) + 0.5

        # 内容匹配
        for mid, mem in self._memories.items():
            content_lower = mem.content.lower()
            for kw in query_keywords:
                if kw.lower() in content_lower:
                    activated[mid] = activated.get(mid, 0) + 0.3
            for mkw in mem.keywords:
                if mkw.lower() in query_lower:
                    activated[mid] = activated.get(mid, 0) + 0.7

        # 第二层：关联扩散
        spread = {}
        for mid, score in activated.items():
            mem = self._memories.get(mid)
            if not mem:
                continue
            for assoc_id in mem.associations:
                if assoc_id not in activated:
                    spread[assoc_id] = spread.get(assoc_id, 0) + score * 0.3
        activated.update({k: v for k, v in spread.items() if k not in activated})

        # 计算最终得分
        results = []
        for mid, relevance in activated.items():
            mem = self._memories.get(mid)
            if not mem:
                continue
            eff_strength = mem.effective_strength()
            if eff_strength < min_strength:
                continue
            emotion_boost = 1.3 if mem.emotion == "important" else 1.0
            final_score = relevance * eff_strength * emotion_boost
            results.append((mem, final_score))

        results.sort(key=lambda x: -x[1])
        top = results[:max_results]

        for mem, _ in top:
            self._reinforce(mem.id)
        self._save()
        return top

    # ── 列表/统计 ──

    def list_all(self, layer=None, sort_by="strength"):
        mems = list(self._memories.values())
        if layer:
            mems = [m for m in mems if m.layer == layer]

        sort_map = {
            "strength": lambda m: -m.effective_strength(),
            "recent": lambda m: -m.last_accessed,
            "created": lambda m: -m.created,
            "access": lambda m: -m.access_count,
        }
        mems.sort(key=sort_map.get(sort_by, sort_map["strength"]))
        return mems

    def get_stats(self):
        layers = defaultdict(int)
        total_strength = 0
        for m in self._memories.values():
            layers[m.layer] += 1
            total_strength += m.effective_strength()
        return {
            "total_memories": len(self._memories),
            "total_keywords": len(self._keyword_index),
            "layers": dict(layers),
            "avg_strength": round(total_strength / max(1, len(self._memories)), 3),
            "association_links": sum(len(m.associations) for m in self._memories.values()) // 2
        }

    def remove(self, memory_id):
        if memory_id in self._memories:
            self._forget(memory_id)
            self._save()
            return True
        return False

    def decay_all(self):
        forget_threshold = SETTINGS.get("forget_threshold", 0.05)
        to_remove = [mid for mid, mem in self._memories.items()
                     if mem.effective_strength() < forget_threshold]
        for mid in to_remove:
            self._forget(mid)
        self._save()
        return len(to_remove), len(self._memories)

    def export_data(self, filepath=None):
        data = {
            "version": "1.0",
            "exported_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "memories": [m.to_dict() for m in self._memories.values()],
            "stats": self.get_stats()
        }
        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        return data

    def import_data(self, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        imported = 0
        for item_data in data.get("memories", []):
            mi = MemoryItem(item_data)
            if mi.id and mi.id not in self._memories:
                self._memories[mi.id] = mi
                imported += 1
        self._rebuild_index()
        self._save()
        return imported


# ══════════════════════════════════════
#  CLI 格式化输出
# ══════════════════════════════════════

LAYER_NAMES = {"semantic": "语义/知识", "episodic": "情景/事件", "procedural": "程序/习惯"}
EMOTION_MARKS = {"important": "⚡", "positive": "✓", "negative": "✗", "neutral": ""}


def fmt_strength(strength):
    n = int(strength * 5)
    return "●" * n + "○" * (5 - n)


def fmt_time(ts):
    if ts <= 0:
        return "N/A"
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))


def fmt_memory_line(mem, score=None):
    eff = mem.effective_strength()
    layer_tag = LAYER_NAMES.get(mem.layer, mem.layer)
    emo = EMOTION_MARKS.get(mem.emotion, "")
    parts = [f"[{layer_tag}|{fmt_strength(eff)}]{emo}"]
    if score is not None:
        parts.append(f"(相关度:{score:.2f})")
    parts.append(mem.content)
    return " ".join(parts)


def fmt_memory_detail(mem):
    eff = mem.effective_strength()
    lines = [
        f"  ID: {mem.id}",
        f"  层级: {LAYER_NAMES.get(mem.layer, mem.layer)}",
        f"  内容: {mem.content}",
        f"  关键词: {', '.join(mem.keywords)}",
        f"  强度: {fmt_strength(eff)} ({eff:.3f})",
        f"  情感: {mem.emotion}",
        f"  访问次数: {mem.access_count}",
        f"  创建: {fmt_time(mem.created)}",
        f"  最后访问: {fmt_time(mem.last_accessed)}",
    ]
    if mem.associations:
        lines.append(f"  关联: {', '.join(mem.associations[:5])}{'...' if len(mem.associations) > 5 else ''}")
    if mem.tags:
        lines.append(f"  标签: {', '.join(mem.tags)}")
    return "\n".join(lines)


# ══════════════════════════════════════
#  CLI 入口
# ══════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="LY Memory Palace — 记忆宫殿 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
命令示例:
  python palace.py recall "Python 项目结构"
  python palace.py store --layer semantic --keywords "Python,偏好" --content "用户喜欢Python"
  python palace.py store --layer episodic --keywords "会议,决策" --content "决定用React重构" --emotion important
  python palace.py list
  python palace.py list --layer semantic --sort recent
  python palace.py stats
  python palace.py remove --id abc123
  python palace.py decay
  python palace.py export --file backup.json
  python palace.py import --file backup.json
        """
    )
    parser.add_argument("--storage", default=None, help="存储目录（默认: skill目录下的data/）")

    sub = parser.add_subparsers(dest="command", help="命令")

    # recall
    p_recall = sub.add_parser("recall", help="关联唤醒：根据文本检索相关记忆")
    p_recall.add_argument("query", help="查询文本")
    p_recall.add_argument("--max", type=int, default=None, help="最大返回条数")

    # store
    p_store = sub.add_parser("store", help="存入记忆")
    p_store.add_argument("--content", required=True, help="记忆内容")
    p_store.add_argument("--layer", default="semantic", choices=["semantic", "episodic", "procedural"])
    p_store.add_argument("--keywords", default="", help="关键词（逗号分隔）")
    p_store.add_argument("--emotion", default="neutral", choices=["neutral", "positive", "negative", "important"])
    p_store.add_argument("--context", default="", help="创建场景描述")
    p_store.add_argument("--tags", default="", help="标签（逗号分隔）")

    # list
    p_list = sub.add_parser("list", help="列出记忆")
    p_list.add_argument("--layer", default=None, choices=["semantic", "episodic", "procedural"])
    p_list.add_argument("--sort", default="strength", choices=["strength", "recent", "created", "access"])
    p_list.add_argument("--detail", action="store_true", help="显示详细信息")

    # stats
    sub.add_parser("stats", help="显示统计信息")

    # remove
    p_remove = sub.add_parser("remove", help="删除记忆")
    p_remove.add_argument("--id", required=True, dest="memory_id", help="记忆 ID")

    # decay
    sub.add_parser("decay", help="手动触发全局衰减清理")

    # export
    p_export = sub.add_parser("export", help="导出记忆备份")
    p_export.add_argument("--file", default=None, help="导出文件路径（默认输出到 stdout）")

    # import
    p_import = sub.add_parser("import", help="导入记忆")
    p_import.add_argument("--file", required=True, help="导入文件路径")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    palace = MemoryPalace(args.storage)

    # ── 执行命令 ──

    if args.command == "recall":
        results = palace.recall(args.query, max_results=args.max)
        if not results:
            print("[记忆宫殿] 未唤醒任何记忆。")
        else:
            print(f"[记忆宫殿] 唤醒 {len(results)} 条记忆：")
            for mem, score in results:
                print(f"  {fmt_memory_line(mem, score)}")

    elif args.command == "store":
        keywords = [k.strip() for k in args.keywords.split(",") if k.strip()] if args.keywords else None
        tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else None
        mid, was_dup = palace.store(
            content=args.content,
            layer=args.layer,
            keywords=keywords,
            tags=tags,
            emotion=args.emotion,
            context=args.context
        )
        if was_dup:
            print(f"[记忆宫殿] 检测到相似记忆，已强化: {mid}")
        else:
            print(f"[记忆宫殿] 已存储新记忆: {mid} [{LAYER_NAMES.get(args.layer, args.layer)}]")

    elif args.command == "list":
        mems = palace.list_all(layer=args.layer, sort_by=args.sort)
        if not mems:
            print("[记忆宫殿] 暂无记忆。")
        else:
            layer_label = LAYER_NAMES.get(args.layer, "全部") if args.layer else "全部"
            print(f"[记忆宫殿] {layer_label} — 共 {len(mems)} 条：")
            for mem in mems:
                if args.detail:
                    print(fmt_memory_detail(mem))
                    print("  ─────────────────────")
                else:
                    print(f"  {fmt_memory_line(mem)}")
                    if mem.keywords:
                        print(f"    关键词: {', '.join(mem.keywords[:8])}")

    elif args.command == "stats":
        stats = palace.get_stats()
        print("[记忆宫殿] 统计信息：")
        print(f"  总记忆数: {stats['total_memories']}")
        print(f"  关键词索引: {stats['total_keywords']}")
        print(f"  关联链接: {stats['association_links']}")
        print(f"  平均强度: {stats['avg_strength']}")
        layers = stats.get("layers", {})
        for layer, count in layers.items():
            print(f"  {LAYER_NAMES.get(layer, layer)}: {count} 条")

    elif args.command == "remove":
        ok = palace.remove(args.memory_id)
        if ok:
            print(f"[记忆宫殿] 已删除记忆: {args.memory_id}")
        else:
            print(f"[记忆宫殿] 记忆不存在: {args.memory_id}")

    elif args.command == "decay":
        forgotten, remaining = palace.decay_all()
        print(f"[记忆宫殿] 衰减清理完成: 遗忘 {forgotten} 条, 剩余 {remaining} 条")

    elif args.command == "export":
        data = palace.export_data(args.file)
        if args.file:
            print(f"[记忆宫殿] 已导出到: {args.file} ({len(data['memories'])} 条记忆)")
        else:
            print(json.dumps(data, ensure_ascii=False, indent=2))

    elif args.command == "import":
        if not os.path.exists(args.file):
            print(f"[记忆宫殿] 文件不存在: {args.file}")
            return
        imported = palace.import_data(args.file)
        print(f"[记忆宫殿] 已导入 {imported} 条记忆")


if __name__ == "__main__":
    main()
