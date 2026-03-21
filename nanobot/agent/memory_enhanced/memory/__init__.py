"""
Memory Module

记忆分层架构模块：
- Working Memory: 工作记忆 (7±2 信息块，秒级)
- Short-term Memory: 短期记忆 (500 条，小时级)
- Long-term Memory: 长期记忆 (NanobotMemory vault)
- Memory Manager: 记忆管理器 (编码/巩固/遗忘)
"""

from .working import (
    WorkingMemory,
    WorkingMemoryItem,
    get_working_memory,
    reset_working_memory,
)

from .short_term import (
    ShortTermMemory,
    ShortTermMemoryItem,
    get_short_term_memory,
    reset_short_term_memory,
)

from .manager import (
    MemoryManager,
    get_memory_manager,
    reset_memory_manager,
)

__all__ = [
    # Working Memory
    "WorkingMemory",
    "WorkingMemoryItem",
    "get_working_memory",
    "reset_working_memory",
    
    # Short-term Memory
    "ShortTermMemory",
    "ShortTermMemoryItem",
    "get_short_term_memory",
    "reset_short_term_memory",
    
    # Memory Manager
    "MemoryManager",
    "get_memory_manager",
    "reset_memory_manager",
]

__version__ = "1.0.0"
