"""Memory system for persistent agent memory - Enhanced with short-term storage."""

from __future__ import annotations

import asyncio
import json
import weakref
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, List, Optional

from loguru import logger

from nanobot.utils.helpers import ensure_dir, estimate_message_tokens, estimate_prompt_tokens_chain

if TYPE_CHECKING:
    from nanobot.providers.base import LLMProvider
    from nanobot.session.manager import Session, SessionManager


_SAVE_MEMORY_TOOL = [
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Save the memory consolidation result to persistent storage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "history_entry": {
                        "type": "string",
                        "description": "A paragraph summarizing key events/decisions/topics. "
                        "Start with [YYYY-MM-DD HH:MM]. Include detail useful for grep search.",
                    },
                    "memory_update": {
                        "type": "string",
                        "description": "Full updated long-term memory as markdown. Include all existing "
                        "facts plus new ones. Return unchanged if nothing new.",
                    },
                },
                "required": ["history_entry", "memory_update"],
            },
        },
    }
]


def _ensure_text(value: Any) -> str:
    """Normalize tool-call payload values to text for file storage."""
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def _normalize_save_memory_args(args: Any) -> dict[str, Any] | None:
    """Normalize provider tool-call arguments to the expected dict shape."""
    if isinstance(args, str):
        args = json.loads(args)
    if isinstance(args, list):
        return args[0] if args and isinstance(args[0], dict) else None
    return args if isinstance(args, dict) else None

_TOOL_CHOICE_ERROR_MARKERS = (
    "tool_choice",
    "toolchoice",
    "does not support",
    'should be ["none", "auto"]',
)


def _is_tool_choice_unsupported(content: str | None) -> bool:
    """Detect provider errors caused by forced tool_choice being unsupported."""
    text = (content or "").lower()
    return any(m in text for m in _TOOL_CHOICE_ERROR_MARKERS)


class MemoryStore:
    """Enhanced memory: MEMORY.md + HISTORY.md + SQLite short-term storage."""

    _MAX_FAILURES_BEFORE_RAW_ARCHIVE = 3

    def __init__(
        self, 
        workspace: Path,
        provider: Optional[LLMProvider] = None,
        model: str = "qwen3.5-plus",
    ):
        self.workspace = workspace
        self.memory_dir = ensure_dir(workspace / "memory")
        self.memory_file = self.memory_dir / "MEMORY.md"
        self.history_file = self.memory_dir / "HISTORY.md"
        self._consecutive_failures = 0
        
        # 增强记忆：短期记忆和工作记忆
        self.provider = provider
        self.model = model
        self.short_term = None
        self.working = None
        self.manager = None
        self.graph = None  # 知识图谱
        self._enhanced_stats = {
            "encoded_count": 0,
            "consolidated_count": 0,
        }
        
        # 统计缓存
        self._stats_cache = {}
        self._stats_cache_time = 0
        
        # 尝试初始化增强记忆
        self._init_enhanced_memory()
    
    def _init_enhanced_memory(self):
        """初始化增强记忆系统"""
        try:
            from nanobot.agent.memory_enhanced.short_term import ShortTermMemory
            from nanobot.agent.memory_enhanced.working import WorkingMemory
            from nanobot.agent.memory_enhanced.manager import MemoryManager
            from nanobot.agent.memory_enhanced.graph_memory import GraphMemory
            
            # 数据库路径：统一使用 memory/ 目录
            db_path = self.memory_dir / "short_term_memory.db"
            
            # 如果 memory/ 目录数据库不存在，但 workspace 根目录有旧数据库，则迁移
            if not db_path.exists():
                old_db_path = self.workspace / "short_term_memory.db"
                if old_db_path.exists():
                    logger.info(f"Found legacy DB at {old_db_path}, migrating to {db_path}")
                    import shutil
                    shutil.copy2(old_db_path, db_path)
                    logger.info(f"Migration complete, keeping legacy DB as backup")
            
            self.short_term = ShortTermMemory(
                db_path=db_path,
                capacity=500,
                ttl_hours=24
            )
            
            self.working = WorkingMemory(
                capacity=9,
                persistence_path=self.memory_dir / "working_memory.json"
            )
            
            self.manager = MemoryManager(
                working_memory=self.working,
                short_term_memory=self.short_term,
                consolidation_callback=self._on_enhanced_consolidate
            )
            
            # 初始化知识图谱
            graph_db_path = self.memory_dir / "graph_memory.db"
            self.graph = GraphMemory(db_path=graph_db_path)
            
            logger.info("Enhanced memory system initialized (SQLite + Working + Graph)")
        except Exception as e:
            logger.warning(f"Enhanced memory not available: {e}")
            logger.warning("Falling back to standard file-based memory")
    
    def _on_enhanced_consolidate(self, summary: Dict[str, Any], items: List[Any]):
        """增强记忆巩固回调 - 写入长期记忆"""
        if summary and "summary" in summary:
            entry = summary["summary"]
            if entry:
                self.append_history(f"[CONSOLIDATED] {entry}")
                logger.info(f"Enhanced consolidation: {len(items)} items → HISTORY.md")

    def read_long_term(self) -> str:
        if self.memory_file.exists():
            return self.memory_file.read_text(encoding="utf-8")
        return ""

    def write_long_term(self, content: str) -> None:
        self.memory_file.write_text(content, encoding="utf-8")

    def append_history(self, entry: str) -> None:
        with open(self.history_file, "a", encoding="utf-8") as f:
            f.write(entry.rstrip() + "\n\n")

    def get_memory_context(self) -> str:
        long_term = self.read_long_term()
        return f"## Long-term Memory\n{long_term}" if long_term else ""
    
    async def encode_message(
        self,
        content: str,
        role: str,
        channel: str = "telegram",
        chat_id: str = "",
        importance: Optional[float] = None,
        auto_extract_tags: bool = True,
    ) -> dict:
        """
        编码消息到增强记忆系统
        
        Args:
            content: 消息内容
            role: user/assistant/tool
            channel: 频道
            chat_id: 聊天 ID
            importance: 重要性 (0-1, 自动计算如果为 None)
            auto_extract_tags: 是否自动提取标签
        
        Returns:
            编码结果
        """
        if not self.manager:
            return {"success": False, "reason": "enhanced_memory_not_available"}
        
        try:
            # 自动计算重要性
            if importance is None:
                importance = self._calculate_importance(content, role)
            
            # 自动提取标签
            tags = []
            if auto_extract_tags:
                tags = self._extract_tags(content, role)
            
            # 编码到工作记忆和短期记忆
            result = self.manager.encode(
                content=content,
                channel=f"{channel}_{chat_id}" if chat_id else channel,
                role=role,
                importance=importance,
                tags=tags,
                add_to_working=True,
                add_to_short_term=True
            )
            
            self._enhanced_stats["encoded_count"] += 1
            
            # 检查是否需要自动巩固
            await self._maybe_auto_consolidate()
            
            logger.debug(f"Encoded message to enhanced memory: role={role}, len={len(content)}")
            return {"success": True, **result}
            
        except Exception as e:
            logger.error(f"Failed to encode message: {e}")
            return {"success": False, "error": str(e)}
    
    def _calculate_importance(self, content: str, role: str) -> float:
        """自动计算消息重要性"""
        importance = 0.5  # 基础分数
        
        # 角色权重
        if role == "user":
            importance += 0.1
        elif role == "assistant":
            importance += 0.2
        
        # 关键词权重
        important_keywords = ["配置", "决定", "重要", "必须", "记住", "注意", "config", "decision"]
        for keyword in important_keywords:
            if keyword in content.lower():
                importance += 0.1
        
        # 问题权重
        if "?" in content or "？" in content:
            importance += 0.1
        
        # 长度权重
        if len(content) > 50:
            importance += 0.1
        
        return min(importance, 1.0)
    
    def _extract_tags(self, content: str, role: str) -> List[str]:
        """
        从内容中自动提取标签
        
        Args:
            content: 消息内容
            role: 角色 (user/assistant)
            
        Returns:
            标签列表 (最多 6 个)
        """
        tags = []
        content_lower = content.lower()
        
        # 角色标签
        tags.append(f"from_{role}")
        
        # 内容类型标签
        if "?" in content or "？" in content:
            tags.append("question")
        
        # 关键词标签
        tag_keywords = {
            "配置": ["配置", "config", "设置", "setup"],
            "错误": ["错误", "error", "失败", "fail", "bug"],
            "重要": ["重要", "必须", "记住", "注意", "critical"],
            "命令": ["/"],
            "技术": ["代码", "code", "python", "sql", "api", "数据库"],
            "项目": ["项目", "project", "nanobot", "memory"],
            "工作": ["工作", "work", "会议", "任务"],
            "查询": ["查询", "搜索", "find", "search", "查看"],
        }
        
        for tag, keywords in tag_keywords.items():
            if any(kw in content_lower for kw in keywords):
                tags.append(tag)
                if len(tags) >= 6:  # 限制标签数量
                    break
        
        # 时间标签
        hour = datetime.now().hour
        if 6 <= hour < 12:
            tags.append("morning")
        elif 12 <= hour < 18:
            tags.append("afternoon")
        else:
            tags.append("evening")
        
        return tags
    
    async def _maybe_auto_consolidate(self):
        """检查是否需要自动巩固"""
        if not self.short_term or not self.provider:
            return
        
        stats = self.short_term.get_stats()
        if stats["unconsolidated"] > 400:
            await self.consolidate_enhanced_batch()
    
    async def consolidate_enhanced_batch(self, batch_size: int = 100):
        """批量巩固增强记忆"""
        if not self.provider or not self.manager:
            return
        
        try:
            from nanobot.agent.memory_enhanced.llm_consolidation import LLMMemoryConsolidator, consolidate_with_llm
            
            consolidator = LLMMemoryConsolidator(
                llm_provider=self.provider,
                model=self.model
            )
            
            result = await consolidate_with_llm(
                self.manager, consolidator, batch_size
            )
            
            if result.get("consolidated"):
                count = result.get("consolidated_count", 0)
                self._enhanced_stats["consolidated_count"] += count
                logger.info(f"Enhanced consolidation: {count} memories")
        except Exception as e:
            logger.error(f"Enhanced consolidation failed: {e}")
    
    def get_enhanced_context(self, query: str = "", limit: int = 7) -> str:
        """
        获取增强记忆上下文用于 prompt
        
        Args:
            query: 当前查询 (用于搜索相关记忆)
            limit: 工作记忆条数
        
        Returns:
            格式化的上下文字符串
        """
        if not self.manager:
            return ""
        
        try:
            # 获取工作记忆上下文
            context = self.manager.get_context(limit=limit)
            
            # 搜索相关记忆
            if query and self.short_term:
                # 从查询中提取相关标签
                relevant_tags = self._extract_query_tags(query)
                
                # 优先按标签搜索，其次按关键词搜索
                if relevant_tags:
                    search_results = self.manager.search(
                        query=query,
                        tags=relevant_tags,
                        hours=24,
                        limit=3
                    )
                else:
                    search_results = self.manager.search(query, hours=24, limit=3)
                
                if search_results:
                    context += "\n\n## 相关记忆\n"
                    for r in search_results:
                        content = r.get("content", "")[:100]
                        role = r.get("role", "?")
                        tags = r.get("tags", [])
                        tag_str = f" [{', '.join(tags)}]" if tags else ""
                        context += f"- [{role}]{tag_str} {content}\n"
            
            return context if context else ""
            
        except Exception as e:
            logger.warning(f"Failed to get enhanced context: {e}")
            return ""
    
    def _extract_query_tags(self, query: str) -> List[str]:
        """
        从查询中提取相关标签用于检索
        
        Args:
            query: 查询文本
            
        Returns:
            相关标签列表 (最多 3 个)
        """
        tags = []
        query_lower = query.lower()
        
        tag_keywords = {
            "配置": ["配置", "config", "设置"],
            "错误": ["错误", "error", "失败"],
            "命令": ["/"],
            "技术": ["代码", "code", "python", "sql"],
            "项目": ["项目", "project", "nanobot"],
            "查询": ["查询", "搜索", "find", "search"],
            "question": ["?", "？", "怎么", "如何", "哪里", "什么"],
        }
        
        for tag, keywords in tag_keywords.items():
            if any(kw in query_lower for kw in keywords):
                tags.append(tag)
        
        return tags[:3]  # 限制最多 3 个标签
    
    def get_enhanced_stats(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        获取增强记忆统计信息
        
        Args:
            force_refresh: 强制刷新缓存
            
        Returns:
            统计信息字典
        """
        import time
        from pathlib import Path
        
        # 使用缓存 (5 秒内不刷新)
        current_time = time.time()
        if not force_refresh and (current_time - self._stats_cache_time) < 5:
            return self._stats_cache
        
        if not self.manager:
            return {"error": "enhanced_memory_not_available"}
        
        try:
            # 短期记忆统计
            short_term_count = self.short_term.count() if self.short_term else 0
            
            # 工作记忆统计
            working_count = self.working.count() if self.working else 0
            
            # 标签分布统计
            tags_distribution = self._get_tags_distribution()
            
            # 角色分布
            role_distribution = self._get_role_distribution()
            
            # 数据库大小
            db_path = self.memory_dir / "short_term_memory.db"
            db_size = db_path.stat().st_size if db_path.exists() else 0
            
            # 巩固统计
            consolidated_count = self._get_consolidated_count()
            
            # 知识图谱统计
            graph_stats = self._get_graph_stats()
            
            stats = {
                "short_term_count": short_term_count,
                "working_count": working_count,
                "tags_distribution": tags_distribution,
                "role_distribution": role_distribution,
                "database_size_bytes": db_size,
                "database_size_kb": round(db_size / 1024, 2),
                "consolidated_count": consolidated_count,
                "unconsolidated_count": short_term_count - consolidated_count,
                "graph": graph_stats,
            }
            
            # 更新缓存
            self._stats_cache = stats
            self._stats_cache_time = current_time
            
            return stats
            
        except Exception as e:
            logger.warning(f"Failed to get enhanced stats: {e}")
            return {"error": str(e)}
    
    def _get_tags_distribution(self) -> Dict[str, int]:
        """获取标签分布统计"""
        if not self.short_term:
            return {}
        
        try:
            import sqlite3
            db_path = self.memory_dir / "short_term_memory.db"
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # 查询所有标签
            cursor.execute("SELECT tags FROM memory_items WHERE tags != '[]'")
            rows = cursor.fetchall()
            conn.close()
            
            # 统计标签频率
            tag_counts = {}
            import json
            for (tags_json,) in rows:
                tags = json.loads(tags_json)
                for tag in tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
            # 按频率排序
            sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
            return dict(sorted_tags[:20])  # 返回前 20 个标签
            
        except Exception as e:
            logger.warning(f"Failed to get tags distribution: {e}")
            return {}
    
    def _get_role_distribution(self) -> Dict[str, int]:
        """获取角色分布统计"""
        if not self.short_term:
            return {}
        
        try:
            import sqlite3
            db_path = self.memory_dir / "short_term_memory.db"
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            cursor.execute("SELECT role, COUNT(*) FROM memory_items GROUP BY role")
            rows = cursor.fetchall()
            conn.close()
            
            return {role: count for role, count in rows}
            
        except Exception as e:
            logger.warning(f"Failed to get role distribution: {e}")
            return {}
    
    def _get_consolidated_count(self) -> int:
        """获取已巩固的记忆数量"""
        if not self.short_term:
            return 0
        
        try:
            import sqlite3
            db_path = self.memory_dir / "short_term_memory.db"
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM memory_items WHERE consolidated = 1")
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result else 0
            
        except Exception as e:
            logger.warning(f"Failed to get consolidated count: {e}")
            return 0
    
    def _get_graph_stats(self) -> Dict[str, Any]:
        """获取知识图谱统计信息"""
        if not self.graph:
            return {"available": False}
        
        try:
            stats = self.graph.get_stats()
            return {
                "available": True,
                "entity_count": stats.get("entity_count", 0),
                "relation_count": stats.get("relation_count", 0),
                "entity_types": stats.get("entity_types", {}),
            }
        except Exception as e:
            logger.warning(f"Failed to get graph stats: {e}")
            return {"available": False, "error": str(e)}
    
    def add_entity(
        self,
        name: str,
        type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        添加实体到知识图谱
        
        Args:
            name: 实体名称
            type: 实体类型 (person/project/config/technology/organization)
            metadata: 元数据
            
        Returns:
            实体 ID，失败返回 None
        """
        if not self.graph:
            return None
        
        try:
            import uuid
            from nanobot.agent.memory_enhanced.graph_memory import Entity
            
            entity = Entity(
                id=str(uuid.uuid4()),
                name=name,
                type=type,
                metadata=metadata or {}
            )
            success = self.graph.add_entity(entity)
            if success:
                logger.debug(f"Added entity: {name} ({type})")
                return entity.id
            return None
        except Exception as e:
            logger.warning(f"Failed to add entity: {e}")
            return None
    
    def add_relation(
        self,
        source_id: str,
        target_id: str,
        type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        添加关系到知识图谱
        
        Args:
            source_id: 源实体 ID
            target_id: 目标实体 ID
            type: 关系类型
            metadata: 元数据
            
        Returns:
            是否成功
        """
        if not self.graph:
            return False
        
        try:
            import uuid
            from nanobot.agent.memory_enhanced.graph_memory import Relation
            
            relation = Relation(
                id=str(uuid.uuid4()),
                source=source_id,
                target=target_id,
                type=type,
                metadata=metadata or {}
            )
            success = self.graph.add_relation(relation)
            if success:
                logger.debug(f"Added relation: {source_id} -> {target_id} ({type})")
                return True
            return False
        except Exception as e:
            logger.warning(f"Failed to add relation: {e}")
            return False
    
    def search_entities(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索实体
        
        Args:
            query: 搜索词
            limit: 最大返回数量
            
        Returns:
            实体列表
        """
        if not self.graph:
            return []
        
        try:
            entities = self.graph.search_entities(query)
            # 转换为字典
            result = []
            for entity in entities[:limit]:
                result.append({
                    "id": entity.id,
                    "name": entity.name,
                    "type": entity.type,
                    "metadata": entity.metadata,
                })
            return result
        except Exception as e:
            logger.warning(f"Failed to search entities: {e}")
            return []
    
    @staticmethod
    def _format_messages(messages: list[dict]) -> str:
        lines = []
        for message in messages:
            if not message.get("content"):
                continue
            tools = f" [tools: {', '.join(message['tools_used'])}]" if message.get("tools_used") else ""
            lines.append(
                f"[{message.get('timestamp', '?')[:16]}] {message['role'].upper()}{tools}: {message['content']}"
            )
        return "\n".join(lines)

    async def consolidate(
        self,
        messages: list[dict],
        provider: LLMProvider,
        model: str,
    ) -> bool:
        """Consolidate the provided message chunk into MEMORY.md + HISTORY.md."""
        if not messages:
            return True

        current_memory = self.read_long_term()
        prompt = f"""You are a memory consolidation agent. Extract structured, searchable memories from this conversation.

## Extraction Guidelines

Extract and organize the following:

1. **Facts**: User preferences, decisions, project details, technical configurations
2. **Events**: What happened, when, who was involved, outcomes
3. **Tasks**: Action items, deadlines, priorities, status
4. **Relationships**: People mentioned, their roles, contact info
5. **Knowledge**: Technical insights, solutions, references

## Output Format

For `memory_update`, use structured markdown with frontmatter:

```markdown
## Category (e.g., Projects, Config, People, Decisions)

### Item Name
---
type: fact|event|task|decision
date: YYYY-MM-DD
tags: [tag1, tag2]
related: [related items]
---
Detailed content with context. Be specific for future grep search.
```

For `history_entry`, write a searchable paragraph:
- Start with [YYYY-MM-DD HH:MM]
- Include key details: who, what, when, outcome
- Use keywords likely to be searched later

## Current Long-term Memory
{current_memory or "(empty)"}

## Conversation to Process
{self._format_messages(messages)}

Call save_memory tool with your consolidation now."""

        chat_messages = [
            {"role": "system", "content": "You are a memory consolidation agent. Extract structured, searchable memories from conversations. Call save_memory tool with your consolidation."},
            {"role": "user", "content": prompt},
        ]

        try:
            # Use "auto" mode for compatibility with Qwen3.5 and other providers
            # that don't support forced tool_choice (only ["none", "auto"])
            response = await provider.chat_with_retry(
                messages=chat_messages,
                tools=_SAVE_MEMORY_TOOL,
                model=model,
                tool_choice="auto",
            )

            if not response.has_tool_calls:
                logger.warning(
                    "Memory consolidation: LLM did not call save_memory "
                    "(finish_reason={}, content_len={}, content_preview={})",
                    response.finish_reason,
                    len(response.content or ""),
                    (response.content or "")[:200],
                )
                return self._fail_or_raw_archive(messages)

            args = _normalize_save_memory_args(response.tool_calls[0].arguments)
            if args is None:
                logger.warning("Memory consolidation: unexpected save_memory arguments")
                return self._fail_or_raw_archive(messages)

            if "history_entry" not in args or "memory_update" not in args:
                logger.warning("Memory consolidation: save_memory payload missing required fields")
                return self._fail_or_raw_archive(messages)

            entry = args["history_entry"]
            update = args["memory_update"]

            if entry is None or update is None:
                logger.warning("Memory consolidation: save_memory payload contains null required fields")
                return self._fail_or_raw_archive(messages)

            entry = _ensure_text(entry).strip()
            if not entry:
                logger.warning("Memory consolidation: history_entry is empty after normalization")
                return self._fail_or_raw_archive(messages)

            self.append_history(entry)
            update = _ensure_text(update)
            if update != current_memory:
                self.write_long_term(update)

            self._consecutive_failures = 0
            logger.info("Memory consolidation done for {} messages", len(messages))
            return True
        except Exception:
            logger.exception("Memory consolidation failed")
            return self._fail_or_raw_archive(messages)

    def _fail_or_raw_archive(self, messages: list[dict]) -> bool:
        """Increment failure count; after threshold, raw-archive messages and return True."""
        self._consecutive_failures += 1
        if self._consecutive_failures < self._MAX_FAILURES_BEFORE_RAW_ARCHIVE:
            return False
        self._raw_archive(messages)
        self._consecutive_failures = 0
        return True

    def _raw_archive(self, messages: list[dict]) -> None:
        """Fallback: dump raw messages to HISTORY.md without LLM summarization."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.append_history(
            f"[{ts}] [RAW] {len(messages)} messages\n"
            f"{self._format_messages(messages)}"
        )
        logger.warning(
            "Memory consolidation degraded: raw-archived {} messages", len(messages)
        )


class MemoryConsolidator:
    """Owns consolidation policy, locking, and session offset updates."""

    _MAX_CONSOLIDATION_ROUNDS = 5

    _SAFETY_BUFFER = 1024  # extra headroom for tokenizer estimation drift

    def __init__(
        self,
        workspace: Path,
        provider: LLMProvider,
        model: str,
        sessions: SessionManager,
        context_window_tokens: int,
        build_messages: Callable[..., list[dict[str, Any]]],
        get_tool_definitions: Callable[[], list[dict[str, Any]]],
        max_completion_tokens: int = 4096,
    ):
        self.store = MemoryStore(workspace, provider=provider, model=model)
        self.provider = provider
        self.model = model
        self.sessions = sessions
        self.context_window_tokens = context_window_tokens
        self.max_completion_tokens = max_completion_tokens
        self._build_messages = build_messages
        self._get_tool_definitions = get_tool_definitions
        self._locks: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()

    def get_lock(self, session_key: str) -> asyncio.Lock:
        """Return the shared consolidation lock for one session."""
        return self._locks.setdefault(session_key, asyncio.Lock())

    async def consolidate_messages(self, messages: list[dict[str, object]]) -> bool:
        """Archive a selected message chunk into persistent memory."""
        return await self.store.consolidate(messages, self.provider, self.model)

    def pick_consolidation_boundary(
        self,
        session: Session,
        tokens_to_remove: int,
    ) -> tuple[int, int] | None:
        """Pick a user-turn boundary that removes enough old prompt tokens."""
        start = session.last_consolidated
        if start >= len(session.messages) or tokens_to_remove <= 0:
            return None

        removed_tokens = 0
        last_boundary: tuple[int, int] | None = None
        for idx in range(start, len(session.messages)):
            message = session.messages[idx]
            if idx > start and message.get("role") == "user":
                last_boundary = (idx, removed_tokens)
                if removed_tokens >= tokens_to_remove:
                    return last_boundary
            removed_tokens += estimate_message_tokens(message)

        return last_boundary

    def estimate_session_prompt_tokens(self, session: Session) -> tuple[int, str]:
        """Estimate current prompt size for the normal session history view."""
        history = session.get_history(max_messages=0)
        channel, chat_id = (session.key.split(":", 1) if ":" in session.key else (None, None))
        probe_messages = self._build_messages(
            history=history,
            current_message="[token-probe]",
            channel=channel,
            chat_id=chat_id,
        )
        return estimate_prompt_tokens_chain(
            self.provider,
            self.model,
            probe_messages,
            self._get_tool_definitions(),
        )

    async def archive_messages(self, messages: list[dict[str, object]]) -> bool:
        """Archive messages with guaranteed persistence (retries until raw-dump fallback)."""
        if not messages:
            return True
        for _ in range(self.store._MAX_FAILURES_BEFORE_RAW_ARCHIVE):
            if await self.consolidate_messages(messages):
                return True
        return True

    async def maybe_consolidate_by_tokens(self, session: Session) -> None:
        """Loop: archive old messages until prompt fits within safe budget.

        The budget reserves space for completion tokens and a safety buffer
        so the LLM request never exceeds the context window.
        """
        if not session.messages or self.context_window_tokens <= 0:
            return

        lock = self.get_lock(session.key)
        async with lock:
            budget = self.context_window_tokens - self.max_completion_tokens - self._SAFETY_BUFFER
            target = budget // 2
            estimated, source = self.estimate_session_prompt_tokens(session)
            if estimated <= 0:
                return
            if estimated < budget:
                logger.debug(
                    "Token consolidation idle {}: {}/{} via {}",
                    session.key,
                    estimated,
                    self.context_window_tokens,
                    source,
                )
                return

            for round_num in range(self._MAX_CONSOLIDATION_ROUNDS):
                if estimated <= target:
                    return

                boundary = self.pick_consolidation_boundary(session, max(1, estimated - target))
                if boundary is None:
                    logger.debug(
                        "Token consolidation: no safe boundary for {} (round {})",
                        session.key,
                        round_num,
                    )
                    return

                end_idx = boundary[0]
                chunk = session.messages[session.last_consolidated:end_idx]
                if not chunk:
                    return

                logger.info(
                    "Token consolidation round {} for {}: {}/{} via {}, chunk={} msgs",
                    round_num,
                    session.key,
                    estimated,
                    self.context_window_tokens,
                    source,
                    len(chunk),
                )
                if not await self.consolidate_messages(chunk):
                    return
                session.last_consolidated = end_idx
                self.sessions.save(session)

                estimated, source = self.estimate_session_prompt_tokens(session)
                if estimated <= 0:
                    return
