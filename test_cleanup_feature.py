#!/usr/bin/env python3
"""
测试记忆清理功能
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def test_cleanup_stats():
    """测试清理统计"""
    print("\n" + "="*60)
    print("测试：记忆清理统计")
    print("="*60)
    
    try:
        from nanobot.agent.memory_enhanced.short_term import ShortTermMemory
        
        workspace = Path.home() / ".nanobot" / "workspace" / "memory"
        db_path = workspace / "short_term_memory.db"
        
        st = ShortTermMemory(db_path=db_path)
        stats = st.get_cleanup_stats()
        
        print(f"\n📊 清理统计:")
        print(f"  总记忆数：{stats['total']} 条")
        print(f"  7 天前：{stats['older_than_7_days']} 条")
        print(f"  30 天前：{stats['older_than_30_days']} 条")
        print(f"  零访问：{stats['zero_access']} 条")
        print(f"  已巩固：{stats['consolidated']} 条")
        print(f"  数据库大小：{stats['database_size_kb']} KB")
        
        print(f"\n💡 清理建议:")
        rec = stats['cleanup_recommendation']
        if rec['should_cleanup']:
            print(f"  ⚠️  建议清理:")
            for reason in rec['reason']:
                print(f"    - {reason}")
        else:
            print(f"  ✅ 无需清理")
        
        print(f"\n✅ 清理统计测试通过!")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False

def test_cleanup_dry_run():
    """测试清理 (干运行)"""
    print("\n" + "="*60)
    print("测试：清理干运行")
    print("="*60)
    
    try:
        from nanobot.agent.memory_enhanced.short_term import ShortTermMemory
        import sqlite3
        
        workspace = Path.home() / ".nanobot" / "workspace" / "memory"
        db_path = workspace / "short_term_memory.db"
        
        st = ShortTermMemory(db_path=db_path)
        
        # 查询会被清理的记忆数量
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # TTL 过期
        cursor.execute("SELECT COUNT(*) FROM memory_items WHERE consolidated = 0")
        unconsolidated = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"  未巩固记忆：{unconsolidated} 条")
        print(f"  ✅ 干运行测试通过")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        return False

def main():
    """运行测试"""
    print("\n" + "="*60)
    print("  记忆清理功能测试")
    print("  时间：2026-03-21 23:10")
    print("="*60)
    
    tests = [
        ("清理统计", test_cleanup_stats),
        ("清理干运行", test_cleanup_dry_run),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ {name} 测试失败：{e}")
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
        print("\n✅ 清理功能测试通过!")
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())
