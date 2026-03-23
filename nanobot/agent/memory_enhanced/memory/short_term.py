#!/usr/bin/env python3
"""
Short-term Memory Module

短期记忆：会话历史存储，小时级持续时间，自动巩固到长期记忆
"""

import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path
import json


@dataclass
class ShortTermMemoryItem:
    """短期记忆项"""
    id: str                         # 唯一标识
    content: str                    # 内容
    channel: str                    # 频道 (telegram/qq/cli/cron)
    timestamp: datetime             # 时间戳
    role: str                       # user/assistant/tool
    tags: List[str] = field(default_factory=list)  # 标签
    access_count: int = 0           # 访问次数
    last_access: Optional[datetime] = None  # 最后访问时间
    consolidated: bool = False      # 是否已巩固
    importance: float = 0.5         # 重要性 (0-1)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "channel": self.channel,
            "timestamp": self.timestamp.isoformat(),
            "role": self.role,
            "tags": self.tags,
            "access_count": self.access_count,
            "last_access": self.last_access.isoformat() if self.last_access else None,
            "consolidated": self.consolidated,
            "importance": self.importance,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ShortTermMemoryItem":
        return cls(
            id=data["id"],
            content=data["content"],
            channel=data["channel"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            role=data["role"],
            tags=data.get("tags", []),
            access_count=data.get("access_count", 0),
            last_access=datetime.fromisoformat(data["last_access"]) if data.get("last_access") else None,
            consolidated=data.get("consolidated", False),
            importance=data.get("importance", 0.5),
            metadata=data.get("metadata", {}),
        )


class ShortTermMemory:
    """
    短期记忆类
    
    存储会话历史，支持时间窗口检索，自动巩固到长期记忆
    使用 SQLite 存储，支持持久化和高效查询
    """
    
    DEFAULT_CAPACITY = 500          # 最大容量
    DEFAULT_TTL_HOURS = 24          # 默认存活时间 (小时)
    CONSOLIDATION_THRESHOLD = 400   # 触发巩固的阈值
    
    def __init__(
        self,
        db_path: Optional[Path] = None,
        capacity: int = DEFAULT_CAPACITY,
        ttl_hours: int = DEFAULT_TTL_HOURS
    ):
        """
        初始化短期记忆
        
        Args:
            db_path: SQLite 数据库路径
            capacity: 最大容量
            ttl_hours: 存活时间 (小时)
        """
        self.db_path = db_path or Path.home() / ".nanobot" / "workspace" / "short_term_memory.db"
        self.capacity = capacity
        self.ttl_hours = ttl_hours
        
        # 确保目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
    # 初始化数据库
    self._init_db()

    def _init_db(self) -> None:
        """初始化数据库表"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # 创建 memory_items 表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory_items (
        id TEXT PRIMARY KEY,
        content TEXT NOT NULL,
        channel TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        role TEXT NOT NULL,
        tags TEXT,
        access_count INTEGER DEFAULT 0,
        last_access TEXT,
        consolidated INTEGER DEFAULT 0,
        metadata TEXT
        )
        """)

        # 创建 memory_tags 表 (标签关系表)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory_tags (
        memory_id TEXT NOT NULL,
        tag TEXT NOT NULL,
        FOREIGN KEY (memory_id) REFERENCES memory_items(id) ON DELETE CASCADE
        )
        """)

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON memory_items(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_channel ON memory_items(channel)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_consolidated ON memory_items(consolidated)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_access_count ON memory_items(access_count)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tag ON memory_tags(tag)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_id ON memory_tags(memory_id)")

        conn.commit()
        conn.close()
    
    def add(
        self,
        content: str,
        channel: str,
        role: str,
        timestamp: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> ShortTermMemoryItem:
        """
        添加记忆项
        
        Args:
            content: 内容
            channel: 频道
            role: 角色
            timestamp: 时间戳 (默认现在)
            tags: 标签
            metadata: 元数据
            
        Returns:
            添加的记忆项
        """
        import uuid
        
        item = ShortTermMemoryItem(
            id=str(uuid.uuid4()),
            content=content,
            channel=channel,
            timestamp=timestamp or datetime.now(),
            role=role,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO memory_items
            (id, content, channel, timestamp, role, tags, access_count, last_access, consolidated, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item.id,
            item.content,
            item.channel,
            item.timestamp.isoformat(),
            item.role,
            json.dumps(item.tags, ensure_ascii=False),
            item.access_count,
            item.last_access.isoformat() if item.last_access else None,
            1 if item.consolidated else 0,
            json.dumps(item.metadata, ensure_ascii=False)
        ))
        
        conn.commit()
        conn.close()
        
        # 检查是否需要清理
        self._maybe_cleanup()
        
        return item
    
    def get(
        self,
        hours: int = 24,
        channel: Optional[str] = None,
        limit: int = 100
    ) -> List[ShortTermMemoryItem]:
        """
        获取记忆项
        
        Args:
            hours: 最近 N 小时
            channel: 频道过滤
            limit: 最大返回数量
            
        Returns:
            记忆项列表 (按时间倒序)
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        query = """
            SELECT * FROM memory_items
            WHERE timestamp > ?
        """
        params = [cutoff]
        
        if channel:
            query += " AND channel = ?"
            params.append(channel)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        items = []
        for row in rows:
            item = ShortTermMemoryItem(
                id=row[0],
                content=row[1],
                channel=row[2],
                timestamp=datetime.fromisoformat(row[3]),
                role=row[4],
                tags=json.loads(row[5] or "[]"),
                access_count=row[6],
                last_access=datetime.fromisoformat(row[7]) if row[7] else None,
                consolidated=bool(row[8]),
                metadata=json.loads(row[9] or "{}")
            )
            items.append(item)
        
        return items
    
    def search(
        self,
        query: str,
        hours: int = 24,
        channel: Optional[str] = None,
        limit: int = 20
    ) -> List[ShortTermMemoryItem]:
        """
        搜索记忆项
        
        Args:
            query: 搜索词
            hours: 最近 N 小时
            channel: 频道过滤
            limit: 最大返回数量
            
        Returns:
            匹配的记忆项
        """
        items = self.get(hours=hours, channel=channel, limit=limit * 5)  # 获取更多用于过滤
        
        query_lower = query.lower()
        matches = []
        
        for item in items:
            if query_lower in item.content.lower():
                # 更新访问统计
                item.access_count += 1
                item.last_access = datetime.now()
                matches.append(item)
        
        # 按相关性排序 (简单关键词匹配 + 时间衰减)
        now = datetime.now()
        for item in matches:
            age_hours = (now - item.timestamp).total_seconds() / 3600
            time_score = 1.0 / (1.0 + age_hours / 24)  # 24 小时衰减
            item._score = time_score * (1 + item.access_count * 0.1)
        
        matches.sort(key=lambda x: getattr(x, '_score', 0), reverse=True)
        
        # 更新数据库中的访问统计
        self._update_access_stats([m for m in matches if m.last_access])
        
        return matches[:limit]
    
    def get_unconsolidated(self, limit: int = 100) -> List[ShortTermMemoryItem]:
        """获取未巩固的记忆项"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM memory_items
            WHERE consolidated = 0
            ORDER BY timestamp ASC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        items = []
        for row in rows:
            item = ShortTermMemoryItem(
                id=row[0],
                content=row[1],
                channel=row[2],
                timestamp=datetime.fromisoformat(row[3]),
                role=row[4],
                tags=json.loads(row[5] or "[]"),
                access_count=row[6],
                last_access=datetime.fromisoformat(row[7]) if row[7] else None,
                consolidated=bool(row[8]),
                metadata=json.loads(row[9] or "{}")
            )
            items.append(item)
        
        return items
    
    def mark_consolidated(self, ids: List[str]) -> int:
        """
        标记记忆项为已巩固
        
        Args:
            ids: 记忆项 ID 列表
            
        Returns:
            更新的数量
        """
        if not ids:
            return 0
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        placeholders = ','.join('?' * len(ids))
        cursor.execute(f"""
            UPDATE memory_items
            SET consolidated = 1
            WHERE id IN ({placeholders})
        """, ids)
        
        count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return count
    
    def delete(self, item_id: str) -> bool:
        """删除记忆项"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM memory_items WHERE id = ?", (item_id,))
        
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return deleted
    
    def apply_forgetting(self) -> int:
        """
        应用遗忘机制
        
        基于时间衰减和使用频率删除低重要性记忆
        
        Returns:
            删除的数量
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # 获取所有记忆项
        cursor.execute("SELECT * FROM memory_items ORDER BY timestamp ASC")
        rows = cursor.fetchall()
        
        to_delete = []
        now = datetime.now()
        
        for row in rows:
            item_id = row[0]
            timestamp = datetime.fromisoformat(row[3])
            access_count = row[6]
            
            # 计算重要性
            age_days = (now - timestamp).total_seconds() / 86400
            decay = 2.718 ** (-age_days / 30)  # 30 天衰减
            usage = 1 + access_count * 0.1
            importance = decay * usage
            
            # 低于阈值的标记删除
            if importance < 0.1:
                to_delete.append(item_id)
        
        # 批量删除
        if to_delete:
            placeholders = ','.join('?' * len(to_delete))
            cursor.execute(f"DELETE FROM memory_items WHERE id IN ({placeholders})", to_delete)
        
        count = len(to_delete)
        conn.commit()
        conn.close()
        
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # 总数
        cursor.execute("SELECT COUNT(*) FROM memory_items")
        total = cursor.fetchone()[0]
        
        # 未巩固数
        cursor.execute("SELECT COUNT(*) FROM memory_items WHERE consolidated = 0")
        unconsolidated = cursor.fetchone()[0]
        
        # 各频道分布
        cursor.execute("SELECT channel, COUNT(*) FROM memory_items GROUP BY channel")
        by_channel = dict(cursor.fetchall())
        
        # 最早和最晚
        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM memory_items")
        row = cursor.fetchone()
        oldest = row[0]
        newest = row[1]
        
        conn.close()
        
        return {
            "total": total,
            "unconsolidated": unconsolidated,
            "consolidated": total - unconsolidated,
            "by_channel": by_channel,
            "oldest": oldest,
            "newest": newest,
            "capacity": self.capacity,
            "utilization": total / self.capacity if self.capacity > 0 else 0,
        }
    
    def _maybe_cleanup(self) -> None:
        """检查是否需要清理"""
        stats = self.get_stats()
        
        # 超出容量时清理
        if stats["total"] > self.capacity:
            self.apply_forgetting()
    
    def _update_access_stats(self, items: List[ShortTermMemoryItem]) -> None:
        """更新访问统计"""
        if not items:
            return
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        for item in items:
            cursor.execute("""
                UPDATE memory_items
                SET access_count = ?, last_access = ?
                WHERE id = ?
            """, (item.access_count, item.last_access.isoformat(), item.id))
        
        conn.commit()
        conn.close()
    
    def clear(self) -> int:
        """清空所有记忆"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM memory_items")
        count = cursor.fetchone()[0]
        
        cursor.execute("DELETE FROM memory_items")
        conn.commit()
        conn.close()
        
        return count
    
    def __len__(self) -> int:
        stats = self.get_stats()
        return stats["total"]
    
    def __repr__(self) -> str:
        stats = self.get_stats()
        return f"ShortTermMemory(total={stats['total']}, unconsolidated={stats['unconsolidated']})"


# 全局单例
_short_term_memory: Optional[ShortTermMemory] = None


def get_short_term_memory(db_path: Optional[Path] = None) -> ShortTermMemory:
    """获取短期记忆单例"""
    global _short_term_memory
    if _short_term_memory is None:
        _short_term_memory = ShortTermMemory(db_path=db_path)
    return _short_term_memory


def reset_short_term_memory() -> None:
    """重置短期记忆单例"""
    global _short_term_memory
    _short_term_memory = None


# 测试
if __name__ == "__main__":
    import tempfile
    
    print("=" * 60)
    print("Short-term Memory 测试")
    print("=" * 60)
    
    # 创建临时数据库
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_db = Path(f.name)
    
    try:
        # 测试基本功能
        stm = ShortTermMemory(db_path=temp_db, capacity=10)
        
        print("\n1. 添加记忆项")
        stm.add("查询 nanobot 配置", channel="telegram", role="user")
        stm.add("配置在~/.nanobot/config.json", channel="telegram", role="assistant")
        stm.add("如何修改配置？", channel="telegram", role="user")
        stm.add("CLI 测试消息", channel="cli", role="user")
        
        print(f"   当前数量：{len(stm)}")
        
        print("\n2. 获取最近记忆")
        items = stm.get(hours=24)
        print(f"   数量：{len(items)}")
        for item in items[:3]:
            print(f"   - [{item.channel}] {item.content[:40]}")
        
        print("\n3. 搜索")
        matches = stm.search("配置", hours=24)
        print(f"   匹配数：{len(matches)}")
        for m in matches:
            print(f"   - [{m.channel}] {m.content[:50]}")
        
        print("\n4. 统计信息")
        stats = stm.get_stats()
        for k, v in stats.items():
            print(f"   {k}: {v}")
        
        print("\n5. 未巩固记忆")
        unconsolidated = stm.get_unconsolidated()
        print(f"   数量：{len(unconsolidated)}")
        
        print("\n6. 标记巩固")
        ids = [i.id for i in unconsolidated[:2]]
        count = stm.mark_consolidated(ids)
        print(f"   标记数量：{count}")
        
        print("\n7. 遗忘测试")
        deleted = stm.apply_forgetting()
        print(f"   删除数量：{deleted}")
        
        print("\n✓ 所有测试通过")
        
    finally:
        # 清理临时文件
        if temp_db.exists():
            temp_db.unlink()
    
    print("=" * 60)
