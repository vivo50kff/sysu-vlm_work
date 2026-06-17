"""
VLM服务模块 - 支持多种云端API，根据图像类型注入系统提示词
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import base64
import httpx
from loguru import logger

from app.config import settings

# 系统提示词模板（按图像类型）
SYSTEM_PROMPTS = {
    "natural_scene": "你是一个智能图文问答助手。请根据用户提供的自然场景图片和问题，给出准确、详细的中文回答。要求：1. 仔细观察图片中的所有元素（物体、人物、场景、颜色、动作等）；2. 回答要准确、完整，包含具体细节；3. 如果图片中有文字，请识别并引用；4. 可以基于图片内容进行合理的推理。",

    "document": "你是一个专业的文档分析助手。请根据用户提供的文档图片和问题，给出准确、详细的中文回答。要求：1. 识别文档中的所有文字内容（标题、正文、表格数据等）；2. 理解文档结构和层次关系；3. 对表格、图表进行准确解读；4. 回答要专业、准确，引用原文关键信息；5. 可以总结、概括文档的主要内容。",

    "slide": "你是一个课件/幻灯片分析助手。请根据用户提供的幻灯片图片和问题，给出准确、详细的中文回答。要求：1. 识别幻灯片中的所有文字和图表；2. 理解幻灯片的逻辑结构和要点层次；3. 对图表、示意图进行解读；4. 回答要结构清晰，突出要点；5. 可以补充相关知识点的解释。",

    "product": "你是一个电商商品分析助手。请根据用户提供的商品图片和问题，给出准确、详细的中文回答。要求：1. 仔细观察商品的外观、特征、品牌标识等；2. 描述商品的类型、功能、特点；3. 如果图片中有规格参数，请准确识别；4. 可以提供使用建议或对比分析；5. 回答要客观、实用。",

    "general": "你是一个智能图文问答助手。请根据用户提供的图片和问题，给出准确、详细的中文回答。要求：1. 仔细观察图片中的所有细节；2. 回答要准确、完整；3. 如果涉及到图片中的文字，请准确识别；4. 可以基于图片内容进行合理的推理和分析；5. 使用清晰流畅的中文表达。",
}


class VLMServiceBase(ABC):
    """VLM服务基类"""

    @abstractmethod
    async def chat(
        self,
        message: str,
        image_base64: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        image_type: str = "natural_scene"
    ) -> str:
        """
        发送聊天请求

        Args:
            message: 用户消息
            image_base64: base64编码的图片
            history: 对话历史
            image_type: 图像类型，用于选择系统提示词

        Returns:
            模型回复
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """检查API是否可用"""
        pass

    def _get_system_prompt(self, image_type: str) -> str:
        """根据图像类型获取对应的系统提示词"""
        return SYSTEM_PROMPTS.get(image_type, SYSTEM_PROMPTS["general"])


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
        history: Optional[List[Dict[str, str]]] = None,
        image_type: str = "natural_scene"
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

        # 构建消息列表
        messages = []

        # 系统提示词（仅首轮有 history 为空时注入，避免每轮重复）
        if not history:
            messages.append({
                "role": "system",
                "content": [{"text": self._get_system_prompt(image_type)}]
            })

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
        history: Optional[List[Dict[str, str]]] = None,
        image_type: str = "natural_scene"
    ) -> str:
        """调用智谱AI GLM-4V API"""

        # 构建消息
        messages = []

        # 系统提示词（仅首轮，无 history 时注入）
        if not history:
            messages.append({
                "role": "system",
                "content": self._get_system_prompt(image_type)
            })

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