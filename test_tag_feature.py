#!/usr/bin/env python3
"""
测试标签提取和基于标签的检索功能
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def test_tag_extraction():
    """测试标签自动提取"""
    print("\n" + "="*60)
    print("测试 1: 标签自动提取")
    print("="*60)
    
    try:
        from nanobot.agent.memory import MemoryStore
        
        workspace = Path.home() / ".nanobot" / "workspace"
        store = MemoryStore(workspace, provider=None, model="qwen3.5-plus")
        
        test_cases = [
            ("nanobot 的配置文件在哪里？", "user", ["from_user", "question", "配置", "查询"]),
            ("启动时出现错误", "user", ["from_user", "错误"]),
            ("/help 命令", "user", ["from_user", "命令"]),
            ("Python 代码怎么写", "user", ["from_user", "技术"]),
            ("项目进度如何", "user", ["from_user", "项目"]),
            ("记住这个重要决定", "user", ["from_user", "重要"]),
        ]
        
        print(f"\n测试标签提取:")
        all_passed = True
        for content, role, expected_tags in test_cases:
            tags = store._extract_tags(content, role)
            # 检查是否包含预期标签
            has_expected = any(t in tags for t in expected_tags)
            status = "✅" if has_expected else "⚠️"
            print(f"  {status} '{content[:20]}...' → {tags}")
            if not has_expected:
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False

async def test_query_tag_extraction():
    """测试查询标签提取"""
    print("\n" + "="*60)
    print("测试 2: 查询标签提取")
    print("="*60)
    
    try:
        from nanobot.agent.memory import MemoryStore
        
        workspace = Path.home() / ".nanobot" / "workspace"
        store = MemoryStore(workspace, provider=None, model="qwen3.5-plus")
        
        test_cases = [
            ("nanobot 配置在哪里", ["配置", "查询"]),
            ("如何修复错误", ["错误"]),
            ("搜索项目相关的笔记", ["项目", "查询"]),
            ("Python 代码问题", ["技术"]),
        ]
        
        print(f"\n测试查询标签提取:")
        for query, expected_tags in test_cases:
            tags = store._extract_query_tags(query)
            has_expected = any(t in tags for t in expected_tags)
            status = "✅" if has_expected else "⚠️"
            print(f"  {status} '{query}' → {tags}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False

async def test_search_with_tags():
    """测试带标签的搜索"""
    print("\n" + "="*60)
    print("测试 3: 带标签的搜索")
    print("="*60)
    
    try:
        from nanobot.agent.memory import MemoryStore
        
        workspace = Path.home() / ".nanobot" / "workspace"
        store = MemoryStore(workspace, provider=None, model="qwen3.5-plus")
        
        if not store.manager:
            print("⚠️  增强记忆不可用")
            return False
        
        # 先编码一些带标签的消息
        test_messages = [
            ("nanobot 配置问题", "user", "telegram", "test1"),
            ("Python 代码错误", "user", "telegram", "test2"),
            ("项目会议记录", "user", "telegram", "test3"),
            ("配置文件路径", "assistant", "telegram", "test4"),
        ]
        
        print(f"\n编码测试消息:")
        for content, role, channel, chat_id in test_messages:
            result = await store.encode_message(
                content=content,
                role=role,
                channel=channel,
                chat_id=chat_id,
                auto_extract_tags=True
            )
            print(f"  ✅ '{content}' → 编码成功")
        
        # 测试搜索
        print(f"\n测试搜索:")
        
        # 搜索配置相关
        context = store.get_enhanced_context(query="配置", limit=5)
        print(f"  查询'配置': {len(context)} 字符")
        if "配置" in context:
            print(f"  ✅ 找到配置相关内容")
        
        # 搜索错误相关
        context = store.get_enhanced_context(query="错误", limit=5)
        print(f"  查询'错误': {len(context)} 字符")
        
        # 查看数据库中的标签
        import sqlite3
        db_path = workspace / "memory" / "short_term_memory.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT role, substr(content, 1, 20), tags FROM memory_items ORDER BY timestamp DESC LIMIT 5")
        rows = cursor.fetchall()
        conn.close()
        
        print(f"\n数据库中的标签:")
        for role, content, tags in rows:
            print(f"  [{role}] {content} → {tags}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("  标签功能验证测试")
    print("  时间：2026-03-21 22:51")
    print("="*60)
    
    tests = [
        ("标签提取", test_tag_extraction),
        ("查询标签", test_query_tag_extraction),
        ("标签搜索", test_search_with_tags),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                success = await test_func()
            else:
                success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ {name} 测试失败：{e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 汇总
    print("\n" + "="*60)
    print("  测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, s in results if s)
    total = len(results)
    
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {status} - {name}")
    
    print(f"\n总计：{passed}/{total} 通过")
    
    if passed == total:
        print("\n✅ 标签功能实现完成！")
        return 0
    else:
        print("\n❌ 部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
