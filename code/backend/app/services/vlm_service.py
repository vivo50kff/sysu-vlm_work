"""
VLM服务模块 - 支持多种云端API
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import base64
import httpx
from loguru import logger

from app.config import settings


class VLMServiceBase(ABC):
    """VLM服务基类"""
    
    @abstractmethod
    async def chat(
        self,
        message: str,
        image_base64: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        发送聊天请求
        
        Args:
            message: 用户消息
            image_base64: base64编码的图片
            history: 对话历史
            
        Returns:
            模型回复
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """检查API是否可用"""
        pass


class QwenVLService(VLMServiceBase):
    """通义千问VL服务"""
    
    def __init__(self):
        self.api_key = settings.dashscope_api_key
        self.model_name = settings.model_name
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
        
    async def chat(
        self,
        message: str,
        image_base64: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """调用通义千问VL API"""
        
        # 构建消息内容
        content = []
        
        # 添加图片
        if image_base64:
            content.append({
                "image": f"data:image/jpeg;base64,{image_base64}"
            })
        
        # 添加文本
        content.append({
            "text": message
        })
        
        # 构建消息
        messages = []
        
        # 添加历史消息
        if history:
            for msg in history[-settings.max_history_length:]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # 添加当前消息
        messages.append({
            "role": "user",
            "content": content
        })
        
        # 构建请求体
        request_body = {
            "model": self.model_name,
            "input": {
                "messages": messages
            },
            "parameters": {
                "max_tokens": settings.max_tokens,
                "temperature": settings.temperature,
                "result_format": "message"
            }
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.base_url,
                    json=request_body,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
                
                # 解析响应
                if "output" in result and "choices" in result["output"]:
                    return result["output"]["choices"][0]["message"]["content"][0]["text"]
                else:
                    logger.error(f"Unexpected response format: {result}")
                    raise Exception("Invalid API response format")
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"API request failed: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error calling Qwen VL API: {str(e)}")
            raise
    
    async def health_check(self) -> bool:
        """检查API是否可用"""
        try:
            # 发送一个简单的测试请求
            await self.chat("你好")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False


class ZhipuVLService(VLMServiceBase):
    """智谱AI GLM-4V服务"""
    
    def __init__(self):
        self.api_key = settings.zhipu_api_key
        self.model_name = "glm-4v"  # GLM-4V模型
        self.base_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        
    async def chat(
        self,
        message: str,
        image_base64: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """调用智谱AI GLM-4V API"""
        
        # 构建消息
        messages = []
        
        # 添加历史消息
        if history:
            for msg in history[-settings.max_history_length:]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # 构建当前消息内容
        content = []
        
        # 添加图片
        if image_base64:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_base64}"
                }
            })
        
        # 添加文本
        content.append({
            "type": "text",
            "text": message
        })
        
        messages.append({
            "role": "user",
            "content": content
        })
        
        # 构建请求体
        request_body = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": settings.max_tokens,
            "temperature": settings.temperature
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.base_url,
                    json=request_body,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
                
                # 解析响应
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"]
                else:
                    logger.error(f"Unexpected response format: {result}")
                    raise Exception("Invalid API response format")
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"API request failed: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error calling Zhipu GLM-4V API: {str(e)}")
            raise
    
    async def health_check(self) -> bool:
        """检查API是否可用"""
        try:
            await self.chat("你好")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False


class VLMServiceFactory:
    """VLM服务工厂"""
    
    @staticmethod
    def create() -> VLMServiceBase:
        """根据配置创建VLM服务实例"""
        provider = settings.vlm_api_provider
        
        if provider == "qwen":
            logger.info("Using Qwen VL service")
            return QwenVLService()
        elif provider == "zhipu":
            logger.info("Using Zhipu GLM-4V service")
            return ZhipuVLService()
        else:
            raise ValueError(f"Unknown VLM provider: {provider}")


# 全局VLM服务实例
vlm_service = VLMServiceFactory.create()