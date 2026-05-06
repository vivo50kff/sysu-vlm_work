"""
API路由
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import Optional
import base64
from datetime import datetime
from loguru import logger

from app.models import (
    ChatRequest, ChatResponse, EvaluationRequest, EvaluationResponse,
    HealthResponse, APIError, MessageRole
)
from app.services import vlm_service, conversation_manager

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    from app.config import settings
    
    return HealthResponse(
        status="healthy",
        api_provider=settings.vlm_api_provider,
        model_name=settings.model_name
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    图文问答接口
    
    Args:
        request: 聊天请求，包含消息、图片（base64）和对话历史
        
    Returns:
        ChatResponse: 模型回复
    """
    try:
        # 获取或创建对话
        if request.conversation_id:
            conversation = conversation_manager.get_conversation(request.conversation_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            conversation_id = conversation_manager.create_conversation()
        
        conversation_id = request.conversation_id or conversation_id
        
        # 获取对话历史
        history = request.history or conversation_manager.get_history(conversation_id)
        
        # 调用VLM服务
        response = await vlm_service.chat(
            message=request.message,
            image_base64=request.image_base64,
            history=history
        )
        
        # 保存消息到对话历史
        conversation_manager.add_message(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=request.message,
            image_url=request.image_base64[:50] if request.image_base64 else None
        )
        conversation_manager.add_message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=response
        )
        
        return ChatResponse(
            response=response,
            conversation_id=conversation_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/upload", response_model=ChatResponse)
async def chat_with_upload(
    message: str = Form(...),
    image: Optional[UploadFile] = File(None),
    conversation_id: Optional[str] = Form(None)
):
    """
    图文问答接口（文件上传方式）
    
    Args:
        message: 用户消息
        image: 上传的图片文件
        conversation_id: 对话ID（可选）
        
    Returns:
        ChatResponse: 模型回复
    """
    try:
        # 处理图片
        image_base64 = None
        if image:
            image_bytes = await image.read()
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # 获取或创建对话
        if conversation_id:
            conversation = conversation_manager.get_conversation(conversation_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            conversation_id = conversation_manager.create_conversation()
        
        # 获取对话历史
        history = conversation_manager.get_history(conversation_id)
        
        # 调用VLM服务
        response = await vlm_service.chat(
            message=message,
            image_base64=image_base64,
            history=history
        )
        
        # 保存消息到对话历史
        conversation_manager.add_message(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=message
        )
        conversation_manager.add_message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=response
        )
        
        return ChatResponse(
            response=response,
            conversation_id=conversation_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    """获取对话历史"""
    conversation = conversation_manager.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {
        "conversation_id": conversation_id,
        "messages": [
            {
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in conversation.messages
        ],
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat()
    }


@router.delete("/conversation/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """删除对话"""
    success = conversation_manager.delete_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {"message": "Conversation deleted successfully"}


@router.post("/conversation/{conversation_id}/clear")
async def clear_conversation(conversation_id: str):
    """清空对话历史"""
    success = conversation_manager.clear_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {"message": "Conversation cleared successfully"}


@router.get("/conversations")
async def list_conversations():
    """列出所有对话"""
    conversations = []
    for conv_id in conversation_manager.list_conversations():
        conv = conversation_manager.get_conversation(conv_id)
        if conv:
            conversations.append({
                "conversation_id": conv_id,
                "message_count": len(conv.messages),
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat()
            })
    
    return {
        "total": len(conversations),
        "conversations": conversations
    }


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate(request: EvaluationRequest):
    """
    评测接口
    
    Args:
        request: 评测请求，包含图片、问题和标准答案
        
    Returns:
        EvaluationResponse: 评测结果
    """
    try:
        # 调用VLM服务
        prediction = await vlm_service.chat(
            message=request.question,
            image_base64=request.image_base64
        )
        
        # 简单的相似度计算（可以后续改进）
        ground_truth = request.ground_truth.lower().strip()
        pred_lower = prediction.lower().strip()
        
        # 检查是否包含关键词
        is_correct = ground_truth in pred_lower or pred_lower in ground_truth
        
        return EvaluationResponse(
            prediction=prediction,
            ground_truth=request.ground_truth,
            is_correct=is_correct,
            similarity_score=1.0 if is_correct else 0.5
        )
        
    except Exception as e:
        logger.error(f"Evaluation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))