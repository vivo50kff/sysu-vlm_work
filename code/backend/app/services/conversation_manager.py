"""
对话管理服务
"""
from typing import Dict, List, Optional
from datetime import datetime
import uuid
from loguru import logger

from app.models import ConversationHistory, ChatMessage, MessageRole


class ConversationManager:
    """对话管理器"""
    
    def __init__(self):
        # 存储所有对话历史
        self._conversations: Dict[str, ConversationHistory] = {}
        
    def create_conversation(self) -> str:
        """创建新对话"""
        conversation_id = str(uuid.uuid4())
        self._conversations[conversation_id] = ConversationHistory(
            conversation_id=conversation_id,
            messages=[]
        )
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
        logger.info(f"Cleared conversation: {conversation_id}")
        return True
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话"""
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            logger.info(f"Deleted conversation: {conversation_id}")
            return True
        return False
    
    def list_conversations(self) -> List[str]:
        """列出所有对话ID"""
        return list(self._conversations.keys())
    
    def get_conversation_count(self) -> int:
        """获取对话数量"""
        return len(self._conversations)


# 全局对话管理器实例
conversation_manager = ConversationManager()