#!/usr/bin/env python3
"""
测试增强记忆系统 - Step 1 验证
"""

import sys
from pathlib import Path

# 使用虚拟环境
sys.path.insert(0, str(Path(__file__).parent))

from nanobot.agent.memory_enhanced.short_term import ShortTermMemory
from nanobot.agent.memory_enhanced.working import WorkingMemory
from nanobot.agent.memory_enhanced.manager import MemoryManager

def test_short_term_memory():
    """测试短期记忆"""
    print("\n" + "="*60)
    print("测试 1: 短期记忆 (ShortTermMemory)")
    print("="*60)
    
    db_path = Path.home() / ".nanobot" / "workspace" / "memory" / "test_short_term.db"
    
    # 创建实例
    stm = ShortTermMemory(db_path=db_path, capacity=500, ttl_hours=24)
    
    # 添加测试数据
    from datetime import datetime
    item = stm.add(
        content="nanobot 的配置文件在~/.nanobot/config.json",
        role="user",
        channel="telegram_test123",
        tags=["config", "nanobot"],
        metadata={"importance": 0.8}
    )
    
    print(f"✓ 添加记忆项：{item.id[:8]}...")
    print(f"  内容：{item.content[:50]}...")
    print(f"  角色：{item.role}")
    print(f"  重要性：{item.importance}")
    
    # 查询
    items = stm.search("", limit=5)
    print(f"✓ 查询最近记忆：{len(items)} 条")
    
    # 统计
    stats = stm.get_stats()
    print(f"✓ 统计信息:")
    print(f"  总数：{stats['total']}")
    print(f"  未巩固：{stats['unconsolidated']}")
    
    # 清理测试数据库
    db_path.unlink(missing_ok=True)
    print("✓ 测试数据库已清理")
    
    return True

def test_working_memory():
    """测试工作记忆"""
    print("\n" + "="*60)
    print("测试 2: 工作记忆 (WorkingMemory)")
    print("="*60)
    
    wm = WorkingMemory(capacity=9)
    
    # 添加测试数据
    wm.add(
        content="用户询问 nanobot 配置",
        role="user",
        importance=0.7
    )
    
    wm.add(
        content="配置文件在~/.nanobot/config.json",
        role="assistant",
        importance=0.8
    )
    
    print(f"✓ 添加 2 条工作记忆")
    
    # 获取上下文
    context = wm.get_context()
    print(f"✓ 获取上下文：{len(context)} 字符")
    print(f"  预览：{context[:100]}...")
    
    # 统计
    stats = wm.get_stats()
    print(f"✓ 统计信息:")
    print(f"  当前数量：{stats['count']}")
    print(f"  容量：{stats['capacity']}")
    
    return True

def test_memory_manager():
    """测试记忆管理器"""
    print("\n" + "="*60)
    print("测试 3: 记忆管理器 (MemoryManager)")
    print("="*60)
    
    wm = WorkingMemory(capacity=9)
    stm = ShortTermMemory(capacity=500)
    
    manager = MemoryManager(
        working_memory=wm,
        short_term_memory=stm
    )
    
    # 编码消息
    result = manager.encode(
        content="测试消息：nanobot 配置位置",
        channel="test",
        role="user",
        importance=0.7,
        add_to_working=True,
        add_to_short_term=True
    )
    
    print(f"✓ 编码消息：{result.get('id', 'N/A')[:8]}...")
    print(f"  工作记忆：{result.get('working', False)}")
    print(f"  短期记忆：{result.get('short_term', False)}")
    
    # 获取上下文
    context = manager.get_context(limit=5)
    print(f"✓ 获取上下文：{len(context)} 字符")
    
    # 搜索
    search_results = manager.search("配置", hours=24, limit=3)
    print(f"✓ 搜索'配置': {len(search_results)} 条结果")
    
    # 统计
    wm_stats = wm.get_stats()
    stm_stats = stm.get_stats()
    print(f"✓ 统计信息:")
    print(f"  工作记忆：{wm_stats['count']} 条")
    print(f"  短期记忆：{stm_stats['total']} 条")
    
    return True

def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("  增强记忆系统 Step 1 验证")
    print("  时间：2026-03-21 21:35")
    print("="*60)
    
    tests = [
        ("短期记忆", test_short_term_memory),
        ("工作记忆", test_working_memory),
        ("记忆管理器", test_memory_manager),
    ]
    
    results = []
    for name, test_func in tests:
        try:
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
        print("\n✅ Step 1 验证完成：所有测试通过！")
        return 0
    else:
        print("\n❌ 部分测试失败，请检查")
        return 1

if __name__ == "__main__":
    sys.exit(main())
