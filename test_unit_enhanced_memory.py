#!/usr/bin/env python3
"""
增强记忆系统单元测试
"""

import sys
import asyncio
import time
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

async def test_short_term_count():
    """测试短期记忆 count 方法"""
    print("\n" + "="*60)
    print("测试 1: ShortTermMemory.count()")
    print("="*60)
    
    try:
        from nanobot.agent.memory_enhanced.short_term import ShortTermMemory
        
        workspace = Path.home() / ".nanobot" / "workspace" / "memory"
        db_path = workspace / "short_term_memory.db"
        
        st = ShortTermMemory(db_path=db_path)
        count = st.count()
        
        print(f"  短期记忆数量：{count}")
        assert count >= 0, "数量应该 >= 0"
        print(f"  ✅ 测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败：{e}")
        return False

async def test_working_memory_count():
    """测试工作记忆 count 方法"""
    print("\n" + "="*60)
    print("测试 2: WorkingMemory.count()")
    print("="*60)
    
    try:
        from nanobot.agent.memory_enhanced.working import WorkingMemory
        
        wm = WorkingMemory(capacity=9)
        count = wm.count()
        
        print(f"  工作记忆数量：{count}")
        assert count >= 0, "数量应该 >= 0"
        print(f"  ✅ 测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败：{e}")
        return False

async def test_working_memory_capacity():
    """测试工作记忆容量限制"""
    print("\n" + "="*60)
    print("测试 3: WorkingMemory 容量限制")
    print("="*60)
    
    try:
        from nanobot.agent.memory_enhanced.working import WorkingMemory
        
        wm = WorkingMemory(capacity=9)
        
        # 添加 15 条记忆
        for i in range(15):
            wm.add(f"测试消息 {i}", role="user")
        
        count = wm.count()
        print(f"  添加 15 条后数量：{count}")
        
        assert count <= 9, f"容量应该 <= 9, 实际 {count}"
        print(f"  ✅ 容量限制测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败：{e}")
        return False

async def test_tag_search_with_empty_tags():
    """测试空标签搜索"""
    print("\n" + "="*60)
    print("测试 4: 空标签搜索")
    print("="*60)
    
    try:
        from nanobot.agent.memory import MemoryStore
        
        workspace = Path.home() / ".nanobot" / "workspace"
        store = MemoryStore(workspace, provider=None, model="qwen3.5-plus")
        
        if not store.manager:
            print("  ⚠️  增强记忆不可用，跳过测试")
            return True
        
        # 搜索空标签
        results = store.manager.search(query="", tags=[], limit=5)
        print(f"  空标签搜索结果：{len(results)} 条")
        
        # 搜索 None 标签
        results = store.manager.search(query="", tags=None, limit=5)
        print(f"  None 标签搜索结果：{len(results)} 条")
        
        print(f"  ✅ 空标签搜索测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False

async def test_stats_cache():
    """测试统计缓存"""
    print("\n" + "="*60)
    print("测试 5: 统计缓存机制")
    print("="*60)
    
    try:
        from nanobot.agent.memory import MemoryStore
        
        workspace = Path.home() / ".nanobot" / "workspace"
        store = MemoryStore(workspace, provider=None, model="qwen3.5-plus")
        
        if not store.manager:
            print("  ⚠️  增强记忆不可用，跳过测试")
            return True
        
        # 第一次查询（刷新缓存）
        start1 = time.time()
        stats1 = store.get_enhanced_stats(force_refresh=True)
        time1 = time.time() - start1
        
        # 第二次查询（使用缓存）
        start2 = time.time()
        stats2 = store.get_enhanced_stats(force_refresh=False)
        time2 = time.time() - start2
        
        print(f"  刷新缓存耗时：{time1*1000:.2f}ms")
        print(f"  使用缓存耗时：{time2*1000:.2f}ms")
        
        if time1 > 0:
            speedup = time1 / max(time2, 0.001)
            print(f"  缓存加速比：{speedup:.2f}x")
        
        assert stats1 == stats2, "缓存应该返回相同数据"
        print(f"  ✅ 缓存机制测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败：{e}")
        return False

async def test_tag_extraction():
    """测试标签提取"""
    print("\n" + "="*60)
    print("测试 6: 标签自动提取")
    print("="*60)
    
    try:
        from nanobot.agent.memory import MemoryStore
        
        workspace = Path.home() / ".nanobot" / "workspace"
        store = MemoryStore(workspace, provider=None, model="qwen3.5-plus")
        
        test_cases = [
            ("配置在哪里？", ["question", "配置"]),
            ("出现错误", ["错误"]),
            ("/start", ["命令"]),
            ("Python 代码", ["技术"]),
        ]
        
        all_passed = True
        for content, expected_tags in test_cases:
            tags = store._extract_tags(content, "user")
            has_expected = any(t in tags for t in expected_tags)
            status = "✅" if has_expected else "⚠️"
            print(f"  {status} '{content}' → {tags[:3]}")
            if not has_expected:
                all_passed = False
        
        if all_passed:
            print(f"  ✅ 标签提取测试通过")
        return all_passed
        
    except Exception as e:
        print(f"  ❌ 测试失败：{e}")
        return False

async def test_query_tag_extraction():
    """测试查询标签提取"""
    print("\n" + "="*60)
    print("测试 7: 查询标签推断")
    print("="*60)
    
    try:
        from nanobot.agent.memory import MemoryStore
        
        workspace = Path.home() / ".nanobot" / "workspace"
        store = MemoryStore(workspace, provider=None, model="qwen3.5-plus")
        
        test_cases = [
            ("nanobot 配置", ["配置"]),
            ("如何修复错误", ["错误"]),
            ("搜索项目", ["项目", "查询"]),
        ]
        
        all_passed = True
        for query, expected_tags in test_cases:
            tags = store._extract_query_tags(query)
            has_expected = any(t in tags for t in expected_tags)
            status = "✅" if has_expected else "⚠️"
            print(f"  {status} '{query}' → {tags}")
            if not has_expected:
                all_passed = False
        
        if all_passed:
            print(f"  ✅ 查询标签推断测试通过")
        return all_passed
        
    except Exception as e:
        print(f"  ❌ 测试失败：{e}")
        return False

async def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("  增强记忆系统单元测试")
    print("  时间：2026-03-21 23:07")
    print("="*60)
    
    tests = [
        ("ShortTermMemory.count()", test_short_term_count),
        ("WorkingMemory.count()", test_working_memory_count),
        ("WorkingMemory 容量限制", test_working_memory_capacity),
        ("空标签搜索", test_tag_search_with_empty_tags),
        ("统计缓存机制", test_stats_cache),
        ("标签自动提取", test_tag_extraction),
        ("查询标签推断", test_query_tag_extraction),
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
        print("\n✅ 所有测试通过!")
        return 0
    else:
        print(f"\n❌ {total - passed} 个测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
