"""
配置管理模块
"""
from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """应用配置"""
    
    # API配置
    vlm_api_provider: Literal["qwen", "zhipu"] = "qwen"
    dashscope_api_key: str = ""
    zhipu_api_key: str = ""
    
    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    
    # 模型配置
    model_name: str = "qwen-vl-plus"
    
    # 对话配置
    max_history_length: int = 10
    max_tokens: int = 2048
    temperature: float = 0.7
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
settings = Settings()