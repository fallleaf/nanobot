#!/usr/bin/env python3
"""
添加标签关系表优化标签存储
"""

import sqlite3
import json
from pathlib import Path

def add_tags_table():
    """添加标签关系表"""
    db_path = Path.home() / ".nanobot" / "workspace" / "memory" / "short_term_memory.db"
    
    print(f"数据库路径：{db_path}")
    print(f"数据库存在：{db_path.exists()}")
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 启用 WAL 模式
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    
    # 创建标签关系表
    print("\n创建 memory_tags 表...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory_tags (
            memory_id TEXT NOT NULL,
            tag TEXT NOT NULL,
            FOREIGN KEY (memory_id) REFERENCES memory_items(id) ON DELETE CASCADE
        )
    """)
    
    # 创建索引
    print("创建索引...")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tag ON memory_tags(tag)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_id ON memory_tags(memory_id)")
    
    # 从现有数据迁移标签
    print("迁移现有标签...")
    cursor.execute("SELECT id, tags FROM memory_items WHERE tags != '[]'")
    rows = cursor.fetchall()
    
    migrated_count = 0
    for memory_id, tags_json in rows:
        tags = json.loads(tags_json)
        for tag in tags:
            cursor.execute(
                "INSERT OR IGNORE INTO memory_tags (memory_id, tag) VALUES (?, ?)",
                (memory_id, tag)
            )
            migrated_count += 1
    
    conn.commit()
    
    # 验证
    cursor.execute("SELECT COUNT(*) FROM memory_tags")
    tag_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT tag) FROM memory_tags")
    unique_tags = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\n✅ 标签表创建完成!")
    print(f"  迁移标签记录：{migrated_count} 条")
    print(f"  标签总数：{tag_count} 条")
    print(f"  唯一标签：{unique_tags} 个")
    
    return True

if __name__ == "__main__":
    add_tags_table()
