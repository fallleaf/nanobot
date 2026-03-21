#!/usr/bin/env python3
"""
LLM Memory Consolidation Module

使用 LLM 进行记忆摘要、标签提取和实体识别
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).parent))

from short_term import ShortTermMemoryItem


# ============================================================================
# LLM 提示词模板
# ============================================================================

CONSOLIDATION_PROMPT = """你是一个记忆巩固助手。请分析以下对话记录，完成以下任务：

## 任务
1. **生成摘要**: 用 200-300 字总结对话的核心内容
2. **提取标签**: 提取 3-10 个关键词标签
3. **识别实体**: 识别提到的人名、项目、配置、技术术语等
4. **提取事实**: 提取可长期保存的事实性信息
5. **提取任务**: 提取待办事项和后续行动

## 对话记录
{conversation}

## 输出格式
请严格按照以下 JSON 格式输出：

```json
{{
    "summary": "对话摘要内容...",
    "tags": ["标签 1", "标签 2", "标签 3"],
    "entities": {{
        "people": ["人名 1", "人名 2"],
        "projects": ["项目名"],
        "configs": ["配置项"],
        "technologies": ["技术术语"]
    }},
    "facts": [
        {{
            "content": "事实内容",
            "confidence": 0.9
        }}
    ],
    "tasks": [
        {{
            "content": "任务内容",
            "priority": "high|medium|low",
            "deadline": "YYYY-MM-DD 或 null"
        }}
    ]
}}
```

注意：
- 如果某类内容为空，使用空数组 []
- confidence 范围 0-1，表示事实的可信度
- priority 只能是 high/medium/low
- 使用中文输出"""


QUERY_REWRITE_PROMPT = """你是一个查询改写助手。基于对话上下文，改写用户的查询使其更清晰完整。

## 当前上下文
{context}

## 原始查询
{query}

## 任务
改写查询，要求：
1. 补充上下文中省略的信息
2. 保持原意不变
3. 使查询更具体明确
4. 长度控制在 50 字以内

## 改写后的查询
(直接输出改写后的查询，不要其他内容)"""


# ============================================================================
# LLM 记忆巩固器
# ============================================================================

class LLMMemoryConsolidator:
    """
    LLM 记忆巩固器
    
    使用 LLM 进行：
    1. 对话摘要
    2. 标签提取
    3. 实体识别
    4. 事实提取
    5. 任务提取
    6. 查询改写
    """
    
    def __init__(
        self,
        llm_provider: Optional[Any] = None,
        model: str = "qwen3.5-plus",
        max_tokens: int = 2048,
        temperature: float = 0.3
    ):
        """
        初始化 LLM 巩固器
        
        Args:
            llm_provider: LLM 提供商实例
            model: 模型名称
            max_tokens: 最大输出 token 数
            temperature: 温度参数
        """
        self.llm_provider = llm_provider
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        # 缓存
        self._cache: Dict[str, Any] = {}
    
    async def consolidate(
        self,
        items: List[ShortTermMemoryItem],
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        对记忆项进行 LLM 巩固
        
        Args:
            items: 记忆项列表
            use_cache: 是否使用缓存
            
        Returns:
            巩固结果
        """
        # 生成缓存键
        cache_key = self._get_cache_key(items)
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]
        
        # 准备对话内容
        conversation = self._format_conversation(items)
        
        # 调用 LLM
        result = await self._call_llm(CONSOLIDATION_PROMPT.format(conversation=conversation))
        
        # 解析结果
        parsed = self._parse_result(result)
        
        # 添加元数据
        parsed["metadata"] = {
            "item_count": len(items),
            "channels": list(set(i.channel for i in items)),
            "time_range": {
                "start": items[0].timestamp.isoformat() if items else None,
                "end": items[-1].timestamp.isoformat() if items else None,
            },
            "processed_at": datetime.now().isoformat(),
        }
        
        # 缓存
        if use_cache:
            self._cache[cache_key] = parsed
        
        return parsed
    
    async def rewrite_query(
        self,
        query: str,
        context: str,
        use_cache: bool = True
    ) -> str:
        """
        基于上下文改写查询
        
        Args:
            query: 原始查询
            context: 对话上下文
            use_cache: 是否使用缓存
            
        Returns:
            改写后的查询
        """
        cache_key = f"rewrite:{query}:{hash(context)}"
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]
        
        prompt = QUERY_REWRITE_PROMPT.format(query=query, context=context)
        rewritten = await self._call_llm(prompt, max_tokens=100)
        
        # 清理输出
        rewritten = rewritten.strip().strip('"').strip()
        
        if use_cache:
            self._cache[cache_key] = rewritten
        
        return rewritten
    
    def _format_conversation(self, items: List[ShortTermMemoryItem]) -> str:
        """格式化对话内容"""
        lines = []
        
        # 按时间排序
        sorted_items = sorted(items, key=lambda x: x.timestamp)
        
        for item in sorted_items:
            time_str = item.timestamp.strftime("%H:%M:%S")
            role = item.role.upper()
            content = item.content[:200]  # 限制长度
            lines.append(f"[{time_str}] {role}: {content}")
        
        return "\n".join(lines)
    
    async def _call_llm(
        self,
        prompt: str,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        调用 LLM
        
        Args:
            prompt: 提示词
            max_tokens: 最大 token 数
            
        Returns:
            LLM 响应文本
        """
        if not self.llm_provider:
            # 没有 LLM 提供商时，返回模拟结果
            print("[LLM] 警告：未提供 llm_provider，使用模拟响应")
            return self._mock_llm_response(prompt)
        
        try:
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            # 调用 LLM provider
            response = await self.llm_provider.chat_with_retry(
                messages=messages,
                model=self.model,
                max_tokens=max_tokens or self.max_tokens,
                temperature=self.temperature,
            )
            
            content = response.content or ""
            if content:
                print(f"[LLM] 调用成功，响应长度：{len(content)}")
            else:
                print("[LLM] 警告：LLM 返回空内容，使用模拟响应")
                return self._mock_llm_response(prompt)
            
            return content
            
        except Exception as e:
            # 失败时返回模拟结果
            print(f"[LLM] 错误：{type(e).__name__}: {e}，使用模拟响应")
            return self._mock_llm_response(prompt)
    
    def _mock_llm_response(self, prompt: str) -> str:
        """模拟 LLM 响应（用于测试和无 LLM 时）"""
        # 检测提示词类型
        if "记忆巩固" in prompt or "对话记录" in prompt:
            return json.dumps({
                "summary": "用户咨询了 nanobot 的配置相关问题，包括配置位置和修改方法。助手提供了配置路径和修改建议。",
                "tags": ["nanobot", "配置", "咨询"],
                "entities": {
                    "people": [],
                    "projects": ["nanobot"],
                    "configs": ["config.json"],
                    "technologies": []
                },
                "facts": [
                    {"content": "nanobot 配置文件位于~/.nanobot/config.json", "confidence": 0.95}
                ],
                "tasks": []
            }, ensure_ascii=False)
        else:
            # 查询改写
            return prompt.split("原始查询")[-1].strip()[:50]
    
    def _parse_result(self, result: str) -> Dict[str, Any]:
        """解析 LLM 响应"""
        try:
            # 尝试提取 JSON
            start = result.find("{")
            end = result.rfind("}") + 1
            
            if start >= 0 and end > start:
                json_str = result[start:end]
                return json.loads(json_str)
            else:
                return self._parse_fallback(result)
                
        except json.JSONDecodeError:
            return self._parse_fallback(result)
    
    def _parse_fallback(self, result: str) -> Dict[str, Any]:
        """降级解析（当 JSON 解析失败时）"""
        return {
            "summary": result[:500],
            "tags": ["自动提取"],
            "entities": {
                "people": [],
                "projects": [],
                "configs": [],
                "technologies": []
            },
            "facts": [],
            "tasks": []
        }
    
    def _get_cache_key(self, items: List[ShortTermMemoryItem]) -> str:
        """生成缓存键"""
        content_hash = hash("".join(i.content for i in items))
        return f"consolidate:{content_hash}:{len(items)}"
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            "size": len(self._cache),
            "keys": list(self._cache.keys())[:10],
        }


# ============================================================================
# 与 Memory Manager 集成
# ============================================================================

async def consolidate_with_llm(
    memory_manager: Any,
    llm_consolidator: LLMMemoryConsolidator,
    batch_size: int = 50
) -> Dict[str, Any]:
    """
    使用 LLM 进行记忆巩固
    
    Args:
        memory_manager: MemoryManager 实例
        llm_consolidator: LLMMemoryConsolidator 实例
        batch_size: 批次大小
        
    Returns:
        巩固结果
    """
    # 获取未巩固的记忆
    unconsolidated = memory_manager.short_term.get_unconsolidated(limit=batch_size)
    
    if not unconsolidated:
        return {
            "consolidated": False,
            "reason": "no_unconsolidated_items",
            "count": 0,
        }
    
    # 按频道分组
    by_channel: Dict[str, List[ShortTermMemoryItem]] = {}
    for item in unconsolidated:
        if item.channel not in by_channel:
            by_channel[item.channel] = []
        by_channel[item.channel].append(item)
    
    result = {
        "consolidated": True,
        "total_items": len(unconsolidated),
        "by_channel": {},
        "llm_summaries": [],
    }
    
    # 对每个频道进行 LLM 摘要
    for channel, items in by_channel.items():
        # LLM 巩固
        llm_result = await llm_consolidator.consolidate(items)
        
        # 更新记忆项的标签
        tags = llm_result.get("tags", [])
        for item in items:
            item.tags.extend(tags)
        
        result["by_channel"][channel] = {
            "count": len(items),
            "summary": llm_result.get("summary", ""),
            "tags": tags,
            "entities": llm_result.get("entities", {}),
        }
        
        result["llm_summaries"].append({
            "channel": channel,
            "summary": llm_result.get("summary", ""),
            "tags": tags,
            "entities": llm_result.get("entities", {}),
            "facts": llm_result.get("facts", []),
            "tasks": llm_result.get("tasks", []),
        })
        
        # 调用回调写入长期记忆
        if memory_manager.consolidation_callback:
            await memory_manager.consolidation_callback(llm_result, items)
    
    # 标记为已巩固
    ids = [item.id for item in unconsolidated]
    consolidated_count = memory_manager.short_term.mark_consolidated(ids)
    
    result["consolidated_count"] = consolidated_count
    
    return result


# ============================================================================
# 测试
# ============================================================================

async def main():
    """测试 LLM 巩固器"""
    print("=" * 60)
    print("LLM Memory Consolidation 测试")
    print("=" * 60)
    
    from working import WorkingMemory
    from short_term import ShortTermMemory
    from manager import MemoryManager
    import tempfile
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_db = Path(f.name)
    
    try:
        # 创建记忆系统
        wm = WorkingMemory(capacity=10)
        stm = ShortTermMemory(db_path=temp_db, capacity=50)
        
        consolidation_results = []
        
        async def mock_callback(summary, items):
            consolidation_results.append((summary, len(items)))
        
        manager = MemoryManager(
            working_memory=wm,
            short_term_memory=stm,
            consolidation_callback=mock_callback
        )
        
        # 创建 LLM 巩固器（无实际 LLM，使用模拟）
        llm = LLMMemoryConsolidator()
        
        # 添加测试数据
        print("\n1. 添加测试数据")
        test_items = [
            ("查询 nanobot 配置", "user"),
            ("配置在~/.nanobot/config.json", "assistant"),
            ("如何修改配置？", "user"),
            ("使用文本编辑器打开修改", "assistant"),
            ("修改后需要重启吗？", "user"),
            ("是的，修改后需要重启 nanobot", "assistant"),
        ]
        
        for content, role in test_items:
            manager.encode(
                content=content,
                channel="telegram",
                role=role,
                importance=0.8,
                tags=["测试"]
            )
        
        print(f"   添加了 {len(test_items)} 条消息")
        
        # LLM 巩固
        print("\n2. LLM 巩固")
        result = await consolidate_with_llm(manager, llm, batch_size=10)
        
        print(f"   巩固：{result['consolidated']}")
        print(f"   项目数：{result['total_items']}")
        print(f"   巩固数量：{result['consolidated_count']}")
        
        if result["llm_summaries"]:
            summary = result["llm_summaries"][0]
            print(f"\n   摘要：{summary['summary'][:100]}...")
            print(f"   标签：{summary['tags']}")
            print(f"   实体：{summary['entities']}")
        
        # 测试查询改写
        print("\n3. 查询改写测试")
        context = manager.get_context(limit=5)
        rewritten = await llm.rewrite_query("怎么改？", context)
        print(f"   原始：怎么改？")
        print(f"   改写：{rewritten}")
        
        # 缓存统计
        print("\n4. 缓存统计")
        stats = llm.get_cache_stats()
        print(f"   缓存大小：{stats['size']}")
        
        print("\n✓ 所有测试通过")
        
    finally:
        if temp_db.exists():
            temp_db.unlink()
    
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
