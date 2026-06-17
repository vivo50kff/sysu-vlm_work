"""
对话管理服务 - 支持内存存储和文件持久化
"""
from typing import Dict, List, Optional
from datetime import datetime
import uuid
import json
import os
from pathlib import Path
from loguru import logger

from app.models import ConversationHistory, ChatMessage, MessageRole


class ConversationManager:
    """对话管理器（支持文件持久化）"""

    def __init__(self, storage_dir: str = "data/conversations"):
        # 存储所有对话历史
        self._conversations: Dict[str, ConversationHistory] = {}
        # 文件存储目录
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        # 是否启用持久化
        self._persist_enabled = True
        # 加载已有对话
        self._load_all()

    def _get_file_path(self, conversation_id: str) -> Path:
        """获取对话存储文件路径"""
        return self._storage_dir / f"{conversation_id}.json"

    def _save_conversation(self, conversation_id: str):
        """保存单个对话到文件"""
        if not self._persist_enabled:
            return

        conv = self._conversations.get(conversation_id)
        if not conv:
            return

        try:
            data = {
                "conversation_id": conv.conversation_id,
                "messages": [
                    {
                        "role": msg.role.value,
                        "content": msg.content,
                        "image_url": msg.image_url,
                        "timestamp": msg.timestamp.isoformat()
                    }
                    for msg in conv.messages
                ],
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat()
            }
            filepath = self._get_file_path(conversation_id)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving conversation {conversation_id}: {e}")

    def _load_all(self):
        """从文件加载所有对话"""
        if not self._storage_dir.exists():
            return

        for filepath in self._storage_dir.glob("*.json"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                conv_id = data["conversation_id"]
                messages = []
                for msg_data in data["messages"]:
                    messages.append(ChatMessage(
                        role=MessageRole(msg_data["role"]),
                        content=msg_data["content"],
                        image_url=msg_data.get("image_url"),
                        timestamp=datetime.fromisoformat(msg_data["timestamp"]) if msg_data.get("timestamp") else datetime.now()
                    ))

                self._conversations[conv_id] = ConversationHistory(
                    conversation_id=conv_id,
                    messages=messages,
                    created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
                    updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now()
                )
            except Exception as e:
                logger.error(f"Error loading conversation from {filepath}: {e}")

        logger.info(f"Loaded {len(self._conversations)} conversations from {self._storage_dir}")

    def create_conversation(self) -> str:
        """创建新对话"""
        conversation_id = str(uuid.uuid4())
        self._conversations[conversation_id] = ConversationHistory(
            conversation_id=conversation_id,
            messages=[]
        )
        self._save_conversation(conversation_id)
        logger.info(f"Created new conversation: {conversation_id}")
        return conversation_id

    def get_conversation(self, conversation_id: str) -> Optional[ConversationHistory]:
        """获取对话历史"""
        return self._conversations.get(conversation_id)

    def add_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        image_url: Optional[str] = None
    ) -> bool:
        """添加消息到对话"""
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            logger.error(f"Conversation not found: {conversation_id}")
            return False

        message = ChatMessage(
            role=role,
            content=content,
            image_url=image_url
        )
        conversation.messages.append(message)
        conversation.updated_at = datetime.now()

        self._save_conversation(conversation_id)
        logger.debug(f"Added {role} message to conversation {conversation_id}")
        return True

    def get_history(self, conversation_id: str) -> List[Dict[str, str]]:
        """获取对话历史（用于API调用）"""
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            return []

        history = []
        for msg in conversation.messages:
            history.append({
                "role": msg.role.value,
                "content": msg.content
            })

        return history

    def clear_conversation(self, conversation_id: str) -> bool:
        """清空对话历史"""
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            return False

        conversation.messages = []
        conversation.updated_at = datetime.now()
        self._save_conversation(conversation_id)
        logger.info(f"Cleared conversation: {conversation_id}")
        return True

    def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话"""
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            # 删除持久化文件
            filepath = self._get_file_path(conversation_id)
            if filepath.exists():
                filepath.unlink()
            logger.info(f"Deleted conversation: {conversation_id}")
            return True
        return False

    def list_conversations(self) -> List[str]:
        """列出所有对话ID（按更新时间倒序）"""
        conversations = sorted(
            self._conversations.items(),
            key=lambda x: x[1].updated_at,
            reverse=True
        )
        return [conv_id for conv_id, _ in conversations]

    def get_conversation_count(self) -> int:
        """获取对话数量"""
        return len(self._conversations)

    def export_conversation(self, conversation_id: str, format: str = "json") -> Optional[str]:
        """
        导出对话

        Args:
            conversation_id: 对话ID
            format: 导出格式 (json / markdown)

        Returns:
            导出内容字符串，或None
        """
        conv = self._conversations.get(conversation_id)
        if not conv:
            return None

        if format == "json":
            data = {
                "conversation_id": conv.conversation_id,
                "messages": [
                    {
                        "role": msg.role.value,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat()
                    }
                    for msg in conv.messages
                ],
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat()
            }
            return json.dumps(data, ensure_ascii=False, indent=2)

        elif format == "markdown":
            lines = [
                f"# 对话记录: {conv.conversation_id}",
                f"",
                f"创建时间: {conv.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
                f"更新时间: {conv.updated_at.strftime('%Y-%m-%d %H:%M:%S')}",
                f"消息数: {len(conv.messages)}",
                f"",
                "---",
                ""
            ]
            for msg in conv.messages:
                role_icon = "👤 用户" if msg.role == MessageRole.USER else "🤖 助手"
                lines.append(f"### {role_icon}")
                lines.append(f"")
                lines.append(msg.content)
                lines.append(f"")
                lines.append(f"*{msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')}*")
                lines.append("")

            return "\n".join(lines)

        return None

    def import_conversation(self, data: str) -> Optional[str]:
        """
        导入对话（JSON格式）

        Returns:
            新对话ID或None
        """
        try:
            imported = json.loads(data)
            conversation_id = str(uuid.uuid4())
            messages = []

            for msg_data in imported.get("messages", []):
                messages.append(ChatMessage(
                    role=MessageRole(msg_data["role"]),
                    content=msg_data["content"],
                    image_url=msg_data.get("image_url"),
                    timestamp=datetime.fromisoformat(msg_data["timestamp"]) if msg_data.get("timestamp") else datetime.now()
                ))

            self._conversations[conversation_id] = ConversationHistory(
                conversation_id=conversation_id,
                messages=messages,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            self._save_conversation(conversation_id)
            logger.info(f"Imported conversation: {conversation_id}")
            return conversation_id
        except Exception as e:
            logger.error(f"Error importing conversation: {e}")
            return None

    def search_conversations(self, keyword: str) -> List[Dict]:
        """搜索对话"""
        results = []
        for conv_id, conv in self._conversations.items():
            matched_messages = []
            for msg in conv.messages:
                if keyword.lower() in msg.content.lower():
                    matched_messages.append({
                        "role": msg.role.value,
                        "content": msg.content[:200],
                        "timestamp": msg.timestamp.isoformat()
                    })

            if matched_messages:
                results.append({
                    "conversation_id": conv_id,
                    "matched_count": len(matched_messages),
                    "messages": matched_messages[:5],  # 最多返回5条匹配消息
                    "created_at": conv.created_at.isoformat(),
                    "updated_at": conv.updated_at.isoformat()
                })

        return results


# 全局对话管理器实例
conversation_manager = ConversationManager()
