#!/usr/bin/env python3
"""
测试记忆统计功能
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def test_memory_stats():
    """测试记忆统计功能"""
    print("\n" + "="*60)
    print("测试：记忆统计功能")
    print("="*60)
    
    try:
        from nanobot.agent.memory import MemoryStore
        
        workspace = Path.home() / ".nanobot" / "workspace"
        store = MemoryStore(workspace, provider=None, model="qwen3.5-plus")
        
        if not store.manager:
            print("⚠️  增强记忆不可用")
            return False
        
        # 获取统计信息
        stats = store.get_enhanced_stats(force_refresh=True)
        
        print(f"\n📊 记忆统计信息:")
        print(f"  短期记忆：{stats.get('short_term_count', 0)} 条")
        print(f"  工作记忆：{stats.get('working_count', 0)} 条")
        print(f"  数据库大小：{stats.get('database_size_kb', 0)} KB")
        print(f"  已巩固：{stats.get('consolidated_count', 0)} 条")
        print(f"  未巩固：{stats.get('unconsolidated_count', 0)} 条")
        
        print(f"\n🏷️  标签分布 (Top 10):")
        tags_dist = stats.get('tags_distribution', {})
        for i, (tag, count) in enumerate(list(tags_dist.items())[:10], 1):
            print(f"  {i}. {tag}: {count} 次")
        
        print(f"\n👤 角色分布:")
        role_dist = stats.get('role_distribution', {})
        for role, count in role_dist.items():
            print(f"  {role}: {count} 条")
        
        # 验证数据
        assert 'short_term_count' in stats, "缺少 short_term_count"
        assert 'working_count' in stats, "缺少 working_count"
        assert 'tags_distribution' in stats, "缺少 tags_distribution"
        assert 'database_size_kb' in stats, "缺少 database_size_kb"
        
        print(f"\n✅ 统计功能测试通过!")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """运行测试"""
    print("\n" + "="*60)
    print("  记忆统计功能测试")
    print("  时间：2026-03-21 23:05")
    print("="*60)
    
    success = await test_memory_stats()
    
    print("\n" + "="*60)
    if success:
        print("✅ 测试通过!")
        return 0
    else:
        print("❌ 测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
