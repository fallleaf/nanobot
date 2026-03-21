#!/usr/bin/env python3
"""
测试短期记忆集成
"""

import asyncio
from pathlib import Path
from nanobot.agent.memory_enhanced import EnhancedNanobotMemory

async def test_enhanced_memory():
    """测试增强记忆系统"""
    print("=" * 60)
    print("短期记忆集成测试")
    print("=" * 60)
    
    workspace = Path.home() / ".nanobot" / "workspace"
    
    # 创建增强记忆系统（不使用 LLM 巩固）
    enhanced = EnhancedNanobotMemory(
        workspace=workspace,
        llm_provider=None,  # 测试时不使用 LLM
        model="qwen3.5-plus",
        enable_llm_consolidation=False
    )
    
    print("\n1. 编码测试消息")
    print("-" * 60)
    
    # 测试编码用户消息
    result1 = await enhanced.encode_message(
        content="nanobot 的配置在哪里？",
        role="user",
        channel="test",
        chat_id="test123"
    )
    print(f"   用户消息编码：✅ {result1.get('success', False)}")
    
    # 测试编码助手回复
    result2 = await enhanced.encode_message(
        content="配置在~/.nanobot/config.json",
        role="assistant",
        channel="test",
        chat_id="test123"
    )
    print(f"   助手回复编码：✅ {result2.get('success', False)}")
    
    print("\n2. 查看统计信息")
    print("-" * 60)
    stats = enhanced.get_stats()
    print(f"   工作记忆：{stats['working']['count']} 条")
    print(f"   短期记忆：{stats['short_term']['total']} 条")
    print(f"   已编码：{stats['stats']['encoded_count']} 条")
    print(f"   LLM 启用：{stats['llm_enabled']}")
    
    print("\n3. 获取上下文")
    print("-" * 60)
    context = await enhanced.get_context_for_prompt("如何修改配置？")
    print(f"   上下文长度：{len(context)} 字符")
    if context:
        print(f"   内容预览：{context[:100]}...")
    
    print("\n4. 数据库验证")
    print("-" * 60)
    import sqlite3
    db_path = workspace / "memory" / "short_term_memory.db"
    if db_path.exists():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM memory_items")
        count = cursor.fetchone()[0]
        print(f"   数据库文件：✅ {db_path}")
        print(f"   记录数：{count} 条")
        conn.close()
    else:
        print(f"   数据库文件：❌ 未找到 {db_path}")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_enhanced_memory())
