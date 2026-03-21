#!/usr/bin/env python3
"""
Memory Manager Module

记忆管理器：统一管理编码、巩固、遗忘流程
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

# 使用相对导入
from .working import WorkingMemory, get_working_memory, WorkingMemoryItem
from .short_term import ShortTermMemory, get_short_term_memory, ShortTermMemoryItem


class MemoryManager:
    """
    记忆管理器
    
    负责：
    1. Encoding (编码): 将输入转换为记忆项
    2. Consolidation (巩固): 将短期记忆摘要转为长期记忆
    3. Forgetting (遗忘): 清理低重要性记忆
    """
    
    def __init__(
        self,
        working_memory: Optional[WorkingMemory] = None,
        short_term_memory: Optional[ShortTermMemory] = None,
        consolidation_callback: Optional[callable] = None
    ):
        """
        初始化记忆管理器
        
        Args:
            working_memory: 工作记忆实例
            short_term_memory: 短期记忆实例
            consolidation_callback: 巩固回调函数 (用于写入长期记忆)
        """
        self.working = working_memory or get_working_memory()
        self.short_term = short_term_memory or get_short_term_memory()
        self.consolidation_callback = consolidation_callback
        
        # 巩固配置
        self.consolidation_threshold = 400  # 触发巩固的阈值
        self.consolidation_batch_size = 50   # 每批巩固数量
    
    def encode(
        self,
        content: str,
        channel: str,
        role: str,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        add_to_working: bool = True,
        add_to_short_term: bool = True
    ) -> Dict[str, Any]:
        """
        编码：将输入转换为记忆项并存储
        
        Args:
            content: 内容
            channel: 频道
            role: 角色
            importance: 重要性 (0-1)
            tags: 标签
            add_to_working: 是否添加到工作记忆
            add_to_short_term: 是否添加到短期记忆
            
        Returns:
            编码结果
        """
        result = {
            "encoded_at": datetime.now().isoformat(),
            "working": None,
            "short_term": None,
        }
        
        # 添加到工作记忆
        if add_to_working:
            wm_item = self.working.add(
                content=content,
                role=role,
                importance=importance
            )
            result["working"] = wm_item.to_dict()
        
        # 添加到短期记忆
        if add_to_short_term:
            stm_item = self.short_term.add(
                content=content,
                channel=channel,
                role=role,
                tags=tags
            )
            result["short_term"] = stm_item.to_dict()
        
        # 检查是否需要巩固
        stats = self.short_term.get_stats()
        if stats["unconsolidated"] > self.consolidation_threshold:
            asyncio.create_task(self.consolidate())
        
        return result
    
    async def consolidate(self, batch_size: Optional[int] = None) -> Dict[str, Any]:
        """
        巩固：将短期记忆摘要转为长期记忆
        
        Args:
            batch_size: 每批处理数量
            
        Returns:
            巩固结果
        """
        batch_size = batch_size or self.consolidation_batch_size
        
        # 获取未巩固的记忆
        unconsolidated = self.short_term.get_unconsolidated(limit=batch_size)
        
        if not unconsolidated:
            return {
                "consolidated": False,
                "reason": "no_unconsolidated_items",
                "count": 0,
            }
        
        # 分组 (按频道)
        by_channel: Dict[str, List[ShortTermMemoryItem]] = {}
        for item in unconsolidated:
            if item.channel not in by_channel:
                by_channel[item.channel] = []
            by_channel[item.channel].append(item)
        
        result = {
            "consolidated": True,
            "total_items": len(unconsolidated),
            "by_channel": {},
            "summaries": [],
        }
        
        # 对每个频道进行摘要
        for channel, items in by_channel.items():
            # 生成摘要
            summary = self._generate_summary(items)
            
            result["by_channel"][channel] = {
                "count": len(items),
                "summary": summary,
            }
            result["summaries"].append({
                "channel": channel,
                "summary": summary,
                "item_count": len(items),
                "time_range": {
                    "start": items[0].timestamp.isoformat(),
                    "end": items[-1].timestamp.isoformat(),
                }
            })
            
            # 调用回调写入长期记忆
            if self.consolidation_callback:
                await self.consolidation_callback(summary, items)
        
        # 标记为已巩固
        ids = [item.id for item in unconsolidated]
        consolidated_count = self.short_term.mark_consolidated(ids)
        
        result["consolidated_count"] = consolidated_count
        
        return result
    
    def _generate_summary(self, items: List[ShortTermMemoryItem]) -> str:
        """
        生成摘要
        
        Args:
            items: 记忆项列表
            
        Returns:
            摘要文本
        """
        if not items:
            return ""
        
        # 简单摘要：按时间排序，取关键内容
        items_sorted = sorted(items, key=lambda x: x.timestamp)
        
        lines = [
            f"# 会话摘要",
            f"**时间范围**: {items_sorted[0].timestamp.strftime('%Y-%m-%d %H:%M')} - {items_sorted[-1].timestamp.strftime('%Y-%m-%d %H:%M')}",
            f"**频道**: {items_sorted[0].channel}",
            f"**消息数**: {len(items_sorted)}",
            "",
            "## 关键内容",
        ]
        
        # 提取关键内容 (重要性高的)
        important_items = [i for i in items_sorted if i.importance > 0.7][:5]
        for item in important_items:
            lines.append(f"- [{item.role}] {item.content[:100]}")
        
        # 标签统计
        all_tags = []
        for item in items_sorted:
            all_tags.extend(item.tags)
        
        if all_tags:
            tag_counts = {}
            for tag in all_tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
            lines.append("")
            lines.append("## 标签")
            for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1])[:10]:
                lines.append(f"- {tag} ({count})")
        
        return "\n".join(lines)
    
    def apply_forgetting(self) -> Dict[str, Any]:
        """
        应用遗忘机制
        
        Returns:
            遗忘结果
        """
        deleted_count = self.short_term.apply_forgetting()
        
        return {
            "forgotten": deleted_count > 0,
            "deleted_count": deleted_count,
            "applied_at": datetime.now().isoformat(),
        }
    
    def get_context(self, limit: int = 7) -> str:
        """
        获取当前上下文 (用于 LLM prompt)
        
        Args:
            limit: 工作记忆项数量
            
        Returns:
            格式化的上下文字符串
        """
        return self.working.get_formatted_context(limit=limit)
    
    def search(
        self,
        query: str,
        hours: int = 24,
        channel: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        搜索短期记忆
        
        Args:
            query: 搜索词
            hours: 最近 N 小时
            channel: 频道过滤
            limit: 最大返回数量
            
        Returns:
            搜索结果
        """
        items = self.short_term.search(
            query=query,
            hours=hours,
            channel=channel,
            limit=limit
        )
        
        return [item.to_dict() for item in items]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取记忆系统统计"""
        return {
            "working": self.working.get_stats(),
            "short_term": self.short_term.get_stats(),
            "timestamp": datetime.now().isoformat(),
        }
    
    def clear(self) -> Dict[str, int]:
        """
        清空所有记忆
        
        Returns:
            清空的数量
        """
        return {
            "working": self.working.clear(),
            "short_term": self.short_term.clear(),
        }


# 全局单例
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager(
    working_memory: Optional[WorkingMemory] = None,
    short_term_memory: Optional[ShortTermMemory] = None,
    consolidation_callback: Optional[callable] = None
) -> MemoryManager:
    """获取记忆管理器单例"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager(
            working_memory=working_memory,
            short_term_memory=short_term_memory,
            consolidation_callback=consolidation_callback
        )
    return _memory_manager


def reset_memory_manager() -> None:
    """重置记忆管理器单例"""
    global _memory_manager
    _memory_manager = None


# 测试
if __name__ == "__main__":
    import asyncio
    import tempfile
    
    print("=" * 60)
    print("Memory Manager 测试")
    print("=" * 60)
    
    async def run_tests():
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_db = Path(f.name)
        
        try:
            # 创建记忆管理器
            from .working import WorkingMemory
            from .short_term import ShortTermMemory
            
            wm = WorkingMemory(capacity=5)
            stm = ShortTermMemory(db_path=temp_db, capacity=20)
            
            async def mock_consolidation(summary, items):
                print(f"   [回调] 巩固 {len(items)} 条记忆")
                print(f"   摘要：{summary[:100]}...")
            
            manager = MemoryManager(
                working_memory=wm,
                short_term_memory=stm,
                consolidation_callback=mock_consolidation
            )
            
            print("\n1. 编码测试")
            result = manager.encode(
                content="查询 nanobot 配置",
                channel="telegram",
                role="user",
                importance=0.8,
                tags=["配置", "nanobot"]
            )
            print(f"   工作记忆：{result['working'] is not None}")
            print(f"   短期记忆：{result['short_term'] is not None}")
            
            print("\n2. 获取上下文")
            context = manager.get_context()
            print(context)
            
            print("\n3. 搜索")
            results = manager.search("配置", hours=24)
            print(f"   匹配数：{len(results)}")
            
            print("\n4. 统计信息")
            stats = manager.get_stats()
            print(f"   工作记忆：{stats['working']['count']} 条")
            print(f"   短期记忆：{stats['short_term']['total']} 条")
            
            print("\n5. 巩固测试")
            # 添加更多记忆
            for i in range(5):
                manager.encode(
                    content=f"测试消息 {i}",
                    channel="telegram",
                    role="user"
                )
            
            consolidation_result = await manager.consolidate()
            print(f"   已巩固：{consolidation_result['consolidated']}")
            print(f"   项目数：{consolidation_result['total_items']}")
            
            print("\n6. 遗忘测试")
            forget_result = manager.apply_forgetting()
            print(f"   已遗忘：{forget_result['forgotten']}")
            print(f"   删除数：{forget_result['deleted_count']}")
            
            print("\n✓ 所有测试通过")
            
        finally:
            if temp_db.exists():
                temp_db.unlink()
    
    asyncio.run(run_tests())
    
    print("=" * 60)
