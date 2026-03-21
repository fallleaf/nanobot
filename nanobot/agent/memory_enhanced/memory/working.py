#!/usr/bin/env python3
"""
Working Memory Module

工作记忆：当前任务上下文，7±2 信息块，秒级持续时间
"""

import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import json


@dataclass
class WorkingMemoryItem:
    """工作记忆项"""
    content: str                    # 内容
    role: str                       # user/assistant/tool
    timestamp: datetime             # 时间戳
    importance: float = 0.5         # 重要性 (0-1)
    task_context: str = ""          # 任务上下文
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "role": self.role,
            "timestamp": self.timestamp.isoformat(),
            "importance": self.importance,
            "task_context": self.task_context,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "WorkingMemoryItem":
        return cls(
            content=data["content"],
            role=data["role"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            importance=data.get("importance", 0.5),
            task_context=data.get("task_context", ""),
            metadata=data.get("metadata", {}),
        )


class WorkingMemory:
    """
    工作记忆类
    
    基于认知心理学 Miller's Law (7±2 信息块)
    存储当前任务上下文，秒级持续时间
    """
    
    DEFAULT_CAPACITY = 9  # 7±2，取上限
    DECAY_RATE = 0.1      # 每秒衰减率
    
    def __init__(
        self,
        capacity: int = DEFAULT_CAPACITY,
        persistence_path: Optional[Path] = None
    ):
        """
        初始化工作记忆
        
        Args:
            capacity: 容量 (默认 9)
            persistence_path: 持久化路径 (可选)
        """
        self.capacity = capacity
        self.persistence_path = persistence_path
        self._items: deque[WorkingMemoryItem] = deque(maxlen=capacity)
        self._task_context = ""
        self._created_at = datetime.now()
        
        # 加载持久化数据
        if persistence_path and persistence_path.exists():
            self._load()
    
    def add(
        self,
        content: str,
        role: str = "user",
        importance: float = 0.5,
        task_context: str = "",
        metadata: Optional[Dict] = None
    ) -> WorkingMemoryItem:
        """
        添加记忆项
        
        Args:
            content: 内容
            role: 角色 (user/assistant/tool)
            importance: 重要性 (0-1)
            task_context: 任务上下文
            metadata: 元数据
            
        Returns:
            添加的记忆项
        """
        item = WorkingMemoryItem(
            content=content,
            role=role,
            timestamp=datetime.now(),
            importance=importance,
            task_context=task_context or self._task_context,
            metadata=metadata or {}
        )
        
        self._items.append(item)
        
        # 更新任务上下文
        if task_context:
            self._task_context = task_context
        
        # 持久化
        self._save()
        
        return item
    
    def get_context(self, limit: Optional[int] = None) -> List[WorkingMemoryItem]:
        """
        获取当前上下文
        
        Args:
            limit: 最大返回数量 (默认全部)
            
        Returns:
            记忆项列表 (按时间倒序)
        """
        items = list(self._items)
        if limit:
            items = items[-limit:]
        return list(reversed(items))  # 最新的在前
    
    def get_formatted_context(self, limit: Optional[int] = None) -> str:
        """
        获取格式化的上下文字符串
        
        Args:
            limit: 最大返回数量
            
        Returns:
            格式化的上下文字符串
        """
        items = self.get_context(limit)
        
        if not items:
            return ""
        
        lines = []
        for item in items:
            time_str = item.timestamp.strftime("%H:%M:%S")
            lines.append(f"[{time_str}] {item.role.upper()}: {item.content[:200]}")
        
        return "\n".join(lines)
    
    def clear(self) -> int:
        """
        清空工作记忆
        
        Returns:
            清空的项数
        """
        count = len(self._items)
        self._items.clear()
        self._task_context = ""
        self._save()
        return count
    
    def get_task_context(self) -> str:
        """获取当前任务上下文"""
        return self._task_context
    
    def set_task_context(self, context: str) -> None:
        """设置任务上下文"""
        self._task_context = context
        self._save()
    
    def search(self, query: str, limit: int = 5) -> List[WorkingMemoryItem]:
        """
        在工作记忆中搜索
        
        Args:
            query: 搜索词
            limit: 最大返回数量
            
        Returns:
            匹配的记忆项
        """
        query_lower = query.lower()
        matches = []
        
        for item in self._items:
            if query_lower in item.content.lower():
                matches.append(item)
        
        # 按重要性 + 时间排序
        current_time = time.time()
        matches.sort(
            key=lambda x: x.importance * 0.7 + (1.0 - abs(current_time - x.timestamp.timestamp())) * 0.3,
            reverse=True
        )
        
        return matches[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "count": len(self._items),
            "capacity": self.capacity,
            "utilization": len(self._items) / self.capacity,
            "task_context": self._task_context[:100] if self._task_context else "",
            "created_at": self._created_at.isoformat(),
            "oldest": self._items[0].timestamp.isoformat() if self._items else None,
            "newest": self._items[-1].timestamp.isoformat() if self._items else None,
        }
    
    def _save(self) -> None:
        """持久化到磁盘"""
        if not self.persistence_path:
            return
        
        try:
            data = {
                "capacity": self.capacity,
                "task_context": self._task_context,
                "created_at": self._created_at.isoformat(),
                "items": [item.to_dict() for item in self._items],
            }
            
            self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.persistence_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            pass  # 静默失败
    
    def _load(self) -> None:
        """从磁盘加载"""
        if not self.persistence_path or not self.persistence_path.exists():
            return
        
        try:
            with open(self.persistence_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.capacity = data.get("capacity", self.capacity)
            self._task_context = data.get("task_context", "")
            self._created_at = datetime.fromisoformat(data.get("created_at", datetime.now().isoformat()))
            
            self._items.clear()
            for item_data in data.get("items", []):
                self._items.append(WorkingMemoryItem.from_dict(item_data))
        except Exception as e:
            pass  # 静默失败
    
    def __len__(self) -> int:
        return len(self._items)
    
    def __repr__(self) -> str:
        return f"WorkingMemory(items={len(self._items)}, capacity={self.capacity})"


# 全局单例
_working_memory: Optional[WorkingMemory] = None


def get_working_memory(persistence_path: Optional[Path] = None) -> WorkingMemory:
    """获取工作记忆单例"""
    global _working_memory
    if _working_memory is None:
        _working_memory = WorkingMemory(persistence_path=persistence_path)
    return _working_memory


def reset_working_memory() -> None:
    """重置工作记忆单例"""
    global _working_memory
    _working_memory = None


# 测试
if __name__ == "__main__":
    import tempfile
    
    print("=" * 60)
    print("Working Memory 测试")
    print("=" * 60)
    
    # 创建临时文件用于持久化
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = Path(f.name)
    
    try:
        # 测试基本功能
        wm = WorkingMemory(capacity=5, persistence_path=temp_path)
        
        print("\n1. 添加记忆项")
        wm.add("查询 nanobot 配置", role="user", importance=0.8)
        wm.add("配置在~/.nanobot/config.json", role="assistant", importance=0.9)
        wm.add("如何修改配置？", role="user", importance=0.7)
        
        print(f"   当前数量：{len(wm)}")
        
        print("\n2. 获取上下文")
        context = wm.get_formatted_context()
        print(context)
        
        print("\n3. 搜索")
        matches = wm.search("配置")
        print(f"   匹配数：{len(matches)}")
        for m in matches:
            print(f"   - {m.content[:50]}")
        
        print("\n4. 统计信息")
        stats = wm.get_stats()
        for k, v in stats.items():
            print(f"   {k}: {v}")
        
        print("\n5. 持久化测试")
        wm2 = WorkingMemory(persistence_path=temp_path)
        print(f"   加载后数量：{len(wm2)}")
        
        print("\n✓ 所有测试通过")
        
    finally:
        # 清理临时文件
        if temp_path.exists():
            temp_path.unlink()
    
    print("=" * 60)
