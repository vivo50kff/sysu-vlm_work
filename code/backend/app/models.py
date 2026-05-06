"""
数据模型定义
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ImageType(str, Enum):
    """图像类型"""
    NATURAL_SCENE = "natural_scene"  # 自然场景
    DOCUMENT = "document"            # 文档
    SLIDE = "slide"                  # 幻灯片


class MessageRole(str, Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    """聊天消息"""
    role: MessageRole
    content: str
    image_url: Optional[str] = None  # 图片URL或base64
    timestamp: datetime = datetime.now()


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    image_base64: Optional[str] = None  # base64编码的图片
    conversation_id: Optional[str] = None
    history: Optional[List[Dict[str, str]]] = None


class ChatResponse(BaseModel):
    """聊天响应"""
    response: str
    conversation_id: str
    timestamp: datetime = datetime.now()


class ConversationHistory(BaseModel):
    """对话历史"""
    conversation_id: str
    messages: List[ChatMessage]
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()


class EvaluationRequest(BaseModel):
    """评测请求"""
    image_base64: str
    question: str
    ground_truth: str
    image_type: ImageType = ImageType.NATURAL_SCENE


class EvaluationResponse(BaseModel):
    """评测响应"""
    prediction: str
    ground_truth: str
    accuracy: Optional[float] = None
    similarity_score: Optional[float] = None
    is_correct: Optional[bool] = None


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    api_provider: str
    model_name: str
    timestamp: datetime = datetime.now()


class APIError(BaseModel):
    """API错误响应"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = datetime.now()