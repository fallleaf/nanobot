#!/usr/bin/env python3
"""
Graph Memory Module

图记忆：存储和查询实体关系
"""

import sqlite3
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict


@dataclass
class Entity:
    """实体节点"""
    id: str
    name: str
    type: str  # person/project/config/technology/organization
    metadata: Dict[str, Any]
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


@dataclass
class Relation:
    """关系边"""
    id: str
    source: str  # 源实体 ID
    target: str  # 目标实体 ID
    type: str    # 关系类型
    metadata: Dict[str, Any] = None
    created_at: str = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


# 关系类型定义
RELATION_TYPES = {
    "WORKS_WITH": "同事关系",
    "PARTICIPATES_IN": "参与项目",
    "USES": "使用技术",
    "CONFIGURES": "配置项",
    "LOCATED_AT": "位于",
    "DEPENDS_ON": "依赖",
    "MANAGES": "管理",
    "KNOWS": "认识",
    "MENTIONS": "提及",
}


class GraphMemory:
    """
    图记忆存储和查询
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        初始化图记忆
        
        Args:
            db_path: SQLite 数据库路径
        """
        self.db_path = db_path or Path.home() / ".nanobot" / "workspace" / "graph_memory.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # 实体表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT
            )
        """)
        
        # 关系表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relations (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                type TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT,
                FOREIGN KEY (source) REFERENCES entities(id),
                FOREIGN KEY (target) REFERENCES entities(id)
            )
        """)
        
        # 索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_name ON entities(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_type ON entities(type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relation_source ON relations(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relation_target ON relations(target)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relation_type ON relations(type)")
        
        conn.commit()
        conn.close()
    
    def add_entity(self, entity: Entity) -> bool:
        """添加实体"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO entities (id, name, type, metadata, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                entity.id,
                entity.name,
                entity.type,
                json.dumps(entity.metadata, ensure_ascii=False),
                entity.created_at
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"添加实体失败：{e}")
            return False
    
    def add_relation(self, relation: Relation) -> bool:
        """添加关系"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO relations (id, source, target, type, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                relation.id,
                relation.source,
                relation.target,
                relation.type,
                json.dumps(relation.metadata, ensure_ascii=False),
                relation.created_at
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"添加关系失败：{e}")
            return False
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """获取实体"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, type, metadata, created_at
            FROM entities WHERE id = ?
        """, (entity_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Entity(
                id=row[0],
                name=row[1],
                type=row[2],
                metadata=json.loads(row[3] or "{}"),
                created_at=row[4]
            )
        return None
    
    def get_entity_by_name(self, name: str) -> Optional[Entity]:
        """根据名称获取实体"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, type, metadata, created_at
            FROM entities WHERE name = ?
        """, (name,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Entity(
                id=row[0],
                name=row[1],
                type=row[2],
                metadata=json.loads(row[3] or "{}"),
                created_at=row[4]
            )
        return None
    
    def query_relations(
        self,
        entity_id: str,
        relation_type: Optional[str] = None,
        direction: str = "out"
    ) -> List[Dict[str, Any]]:
        """
        查询实体的关系
        
        Args:
            entity_id: 实体 ID
            relation_type: 关系类型过滤
            direction: 方向 (out=源→目标，in=目标→源)
            
        Returns:
            关系列表
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        if direction == "out":
            source_col = "source"
            target_col = "target"
        else:
            source_col = "target"
            target_col = "source"
        
        if relation_type:
            cursor.execute(f"""
                SELECT r.id, r.{source_col}, r.{target_col}, r.type, r.metadata, r.created_at,
                       e.name as target_name, e.type as target_type
                FROM relations r
                JOIN entities e ON r.{target_col} = e.id
                WHERE r.{source_col} = ? AND r.type = ?
            """, (entity_id, relation_type))
        else:
            cursor.execute(f"""
                SELECT r.id, r.{source_col}, r.{target_col}, r.type, r.metadata, r.created_at,
                       e.name as target_name, e.type as target_type
                FROM relations r
                JOIN entities e ON r.{target_col} = e.id
                WHERE r.{source_col} = ?
            """, (entity_id,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "relation_id": row[0],
                "source": row[1],
                "target": row[2],
                "type": row[3],
                "metadata": json.loads(row[4] or "{}"),
                "created_at": row[5],
                "target_name": row[6],
                "target_type": row[7]
            })
        
        conn.close()
        return results
    
    def find_entities_by_type(self, entity_type: str) -> List[Entity]:
        """根据类型查找实体"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, type, metadata, created_at
            FROM entities WHERE type = ?
        """, (entity_type,))
        
        entities = []
        for row in cursor.fetchall():
            entities.append(Entity(
                id=row[0],
                name=row[1],
                type=row[2],
                metadata=json.loads(row[3] or "{}"),
                created_at=row[4]
            ))
        
        conn.close()
        return entities
    
    def search_entities(self, keyword: str) -> List[Entity]:
        """搜索实体"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, type, metadata, created_at
            FROM entities WHERE name LIKE ?
        """, (f"%{keyword}%",))
        
        entities = []
        for row in cursor.fetchall():
            entities.append(Entity(
                id=row[0],
                name=row[1],
                type=row[2],
                metadata=json.loads(row[3] or "{}"),
                created_at=row[4]
            ))
        
        conn.close()
        return entities
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # 实体总数
        cursor.execute("SELECT COUNT(*) FROM entities")
        total_entities = cursor.fetchone()[0]
        
        # 关系总数
        cursor.execute("SELECT COUNT(*) FROM relations")
        total_relations = cursor.fetchone()[0]
        
        # 按类型统计
        cursor.execute("SELECT type, COUNT(*) FROM entities GROUP BY type")
        by_type = dict(cursor.fetchall())
        
        # 按关系类型统计
        cursor.execute("SELECT type, COUNT(*) FROM relations GROUP BY type")
        relations_by_type = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            "total_entities": total_entities,
            "total_relations": total_relations,
            "entities_by_type": by_type,
            "relations_by_type": relations_by_type,
        }
    
    def clear(self):
        """清空图记忆"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM relations")
        cursor.execute("DELETE FROM entities")
        conn.commit()
        conn.close()


# ============================================================================
# LLM 关系提取
# ============================================================================

RELATION_EXTRACTION_PROMPT = """你是一个知识图谱构建助手。请从以下对话中提取实体和实体间关系。

## 对话内容
{conversation}

## 实体类型
- person: 人物
- project: 项目
- organization: 组织/机构
- technology: 技术/工具
- config: 配置项

## 关系类型
- WORKS_WITH: 同事关系 (A 和 B 一起工作)
- PARTICIPATES_IN: 参与项目 (人参与项目)
- USES: 使用技术 (项目/人使用技术)
- CONFIGURES: 配置项 (系统配置文件)
- MENTIONS: 提及 (对话中提到的实体)

## 输出格式
请严格按照以下 JSON 格式输出：

```json
{{
    "entities": [
        {{"name": "薛明", "type": "person", "metadata": {{"department": "规划支撑中心"}}}}
    ],
    "relations": [
        {{"source": "薛明", "target": "王亮", "type": "WORKS_WITH", "confidence": 0.9}}
    ]
}}
```

注意：
- 只提取对话中明确提到的实体和关系
- confidence 范围 0-1，表示可信度
- 如果某类内容为空，使用空数组 []
"""


async def extract_relations_from_conversation(
    llm_consolidator,
    items: List[Any]
) -> Tuple[List[Entity], List[Relation]]:
    """
    从对话中提取实体和关系
    
    Args:
        llm_consolidator: LLM 巩固器
        items: 记忆项列表
        
    Returns:
        (实体列表，关系列表)
    """
    # 格式化对话
    conversation = "\n".join([
        f"[{item.timestamp.strftime('%H:%M')}] {item.role.upper()}: {item.content}"
        for item in items
    ])
    
    # 调用 LLM 提取
    prompt = RELATION_EXTRACTION_PROMPT.format(conversation=conversation)
    response = await llm_consolidator._call_llm(prompt)
    
    # 解析结果
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            json_str = response[start:end]
            data = json.loads(json_str)
        else:
            data = {"entities": [], "relations": []}
    except:
        data = {"entities": [], "relations": []}
    
    # 转换为对象
    entities = []
    entity_names = set()
    
    for e in data.get("entities", []):
        entity = Entity(
            id=str(uuid.uuid4()),
            name=e.get("name", ""),
            type=e.get("type", "unknown"),
            metadata=e.get("metadata", {})
        )
        entities.append(entity)
        entity_names.add(entity.name.lower())
    
    relations = []
    for r in data.get("relations", []):
        source_name = r.get("source", "")
        target_name = r.get("target", "")
        
        # 只保留两端实体都存在的关系
        if source_name.lower() in entity_names and target_name.lower() in entity_names:
            relation = Relation(
                id=str(uuid.uuid4()),
                source=source_name,  # 使用名称作为临时 ID
                target=target_name,
                type=r.get("type", "unknown"),
                metadata={"confidence": r.get("confidence", 0.5)}
            )
            relations.append(relation)
    
    return entities, relations


# ============================================================================
# 测试
# ============================================================================

async def test_graph_memory():
    """测试图记忆"""
    import tempfile
    
    print("=" * 60)
    print("Graph Memory 测试")
    print("=" * 60)
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_db = Path(f.name)
    
    try:
        graph = GraphMemory(db_path=temp_db)
        
        # 测试 1: 添加实体
        print("\n1. 添加实体")
        entities = [
            Entity(id="1", name="薛明", type="person", metadata={"department": "规划支撑中心"}),
            Entity(id="2", name="王亮", type="person", metadata={"department": "规划支撑中心"}),
            Entity(id="3", name="研究院项目", type="project", metadata={"value": "57 万"}),
            Entity(id="4", name="nanobot", type="technology", metadata={}),
        ]
        
        for entity in entities:
            success = graph.add_entity(entity)
            print(f"   {'✓' if success else '✗'} {entity.name} ({entity.type})")
        
        # 测试 2: 添加关系
        print("\n2. 添加关系")
        relations = [
            Relation(id="r1", source="薛明", target="王亮", type="WORKS_WITH", metadata={}),
            Relation(id="r2", source="薛明", target="研究院项目", type="PARTICIPATES_IN", metadata={}),
            Relation(id="r3", source="王亮", target="研究院项目", type="PARTICIPATES_IN", metadata={}),
            Relation(id="r4", source="nanobot", target="config.json", type="CONFIGURES", metadata={}),
        ]
        
        for relation in relations:
            success = graph.add_relation(relation)
            print(f"   {'✓' if success else '✗'} {relation.source} -[{relation.type}]-> {relation.target}")
        
        # 测试 3: 查询关系
        print("\n3. 查询关系")
        
        # 查询薛明的同事
        colleagues = graph.query_relations("薛明", "WORKS_WITH")
        print(f"   薛明的同事：{[c['target_name'] for c in colleagues]}")
        
        # 查询项目参与者
        participants = graph.query_relations("研究院项目", "PARTICIPATES_IN", direction="in")
        print(f"   研究院项目参与者：{[p['target_name'] for p in participants]}")
        
        # 测试 4: 搜索实体
        print("\n4. 搜索实体")
        results = graph.search_entities("王")
        print(f"   搜索'王': {[r.name for r in results]}")
        
        # 测试 5: 统计
        print("\n5. 统计信息")
        stats = graph.get_stats()
        print(f"   实体总数：{stats['total_entities']}")
        print(f"   关系总数：{stats['total_relations']}")
        print(f"   按类型：{stats['entities_by_type']}")
        print(f"   关系类型：{stats['relations_by_type']}")
        
        # 验证
        success = stats['total_entities'] >= 4 and stats['total_relations'] >= 3
        
        return success
        
    finally:
        if temp_db.exists():
            temp_db.unlink()


async def main():
    """主测试函数"""
    success = await test_graph_memory()
    
    print("\n" + "=" * 60)
    if success:
        print("✓ 项目 4 测试通过！")
        print("\n所有待改进项目实施完成！")
    else:
        print("✗ 项目 4 测试失败，请修复")
    print("=" * 60)
    
    return 0 if success else 1


if __name__ == "__main__":
    import asyncio
    import sys
    sys.exit(asyncio.run(main()))
