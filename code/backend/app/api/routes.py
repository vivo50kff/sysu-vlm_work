"""
API路由 - 包含对话、评测、案例分析等全部接口
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse, PlainTextResponse
from typing import Optional, List
import base64
import os
from datetime import datetime
from loguru import logger
from pydantic import BaseModel

from app.models import (
    ChatRequest, ChatResponse, EvaluationRequest, EvaluationResponse,
    HealthResponse, APIError, MessageRole
)
from app.services import vlm_service, conversation_manager
from app.services.evaluator import evaluator, DatasetLoader, EvalReport
from app.services.case_analyzer import case_analyzer

router = APIRouter()


# ==================== 健康检查 ====================

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    from app.config import settings

    return HealthResponse(
        status="healthy",
        api_provider=settings.vlm_api_provider,
        model_name=settings.model_name
    )


# ==================== 对话接口 ====================

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
            history=history,
            image_type=request.image_type or "natural_scene"
        )

        # 保存消息到对话历史
        conversation_manager.add_message(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=request.message,
            image_url=request.image_base64 if request.image_base64 else None
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
    conversation_id: Optional[str] = Form(None),
    image_type: Optional[str] = Form("natural_scene")
):
    """
    图文问答接口（文件上传方式）

    Args:
        message: 用户消息
        image: 上传的图片文件
        conversation_id: 对话ID（可选）
        image_type: 图像类型（natural_scene/document/slide/product）

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
            history=history,
            image_type=image_type or "natural_scene"
        )

        # 保存消息到对话历史
        conversation_manager.add_message(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=message,
            image_url=image_base64 if image_base64 else None
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


# ==================== 对话管理接口 ====================

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
                "image_url": msg.image_url,
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
                "preview": conv.messages[-1].content[:100] if conv.messages else "",
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat()
            })

    return {
        "total": len(conversations),
        "conversations": conversations
    }


@router.get("/conversation/{conversation_id}/export")
async def export_conversation(conversation_id: str, format: str = "json"):
    """
    导出对话

    Args:
        conversation_id: 对话ID
        format: 导出格式 (json / markdown)
    """
    content = conversation_manager.export_conversation(conversation_id, format)
    if not content:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if format == "markdown":
        return PlainTextResponse(content, media_type="text/markdown")
    return JSONResponse({"conversation_id": conversation_id, "format": format, "content": content})


@router.post("/conversation/import")
async def import_conversation(data: str = Form(...)):
    """导入对话（JSON格式）"""
    conversation_id = conversation_manager.import_conversation(data)
    if not conversation_id:
        raise HTTPException(status_code=400, detail="Invalid import data")

    return {"message": "Conversation imported successfully", "conversation_id": conversation_id}


@router.get("/conversations/search")
async def search_conversations(keyword: str):
    """搜索对话内容"""
    results = conversation_manager.search_conversations(keyword)
    return {"keyword": keyword, "total": len(results), "results": results}


# ==================== 评测接口 ====================

class BatchEvalRequest(BaseModel):
    """批量评测请求"""
    dataset_type: str = "builtin"  # builtin / vqa_v2 / textvqa / custom
    image_type: str = "natural_scene"  # natural_scene / document
    max_samples: int = 10
    dataset_path: Optional[str] = None  # 数据集路径（留空自动使用标准路径）


class CaseAnalysisRequest(BaseModel):
    """案例分析请求"""
    question: str
    prediction: str
    ground_truth: Optional[str] = None
    image_type: str = "natural_scene"
    is_success: bool = True
    error_type: Optional[str] = None
    analysis: str = ""


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate(request: EvaluationRequest):
    """
    单条评测接口

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

        # 精确匹配和包含匹配
        ground_truth = request.ground_truth.lower().strip()
        pred_lower = prediction.lower().strip()

        exact_match = ground_truth == pred_lower
        contains_match = ground_truth in pred_lower or pred_lower in ground_truth
        is_correct = exact_match or contains_match

        return EvaluationResponse(
            prediction=prediction,
            ground_truth=request.ground_truth,
            is_correct=is_correct,
            similarity_score=1.0 if is_correct else 0.5
        )

    except Exception as e:
        logger.error(f"Evaluation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evaluate/datasets")
async def get_dataset_status():
    """
    获取所有数据集的可用状态。

    Returns:
        datasets 列表，每个包含 key/name/available/path/has_images/description/download_url/note/missing_files
    """
    return DatasetLoader.check_dataset_availability()


@router.post("/evaluate/batch")
async def batch_evaluate(request: BatchEvalRequest):
    """
    批量评测接口 - 在数据集上评测模型。

    数据集路径为空时自动使用标准路径 (data/datasets/)；
    如果标准路径下数据集不存在，返回明确错误而非静默降级。
    """
    try:
        # 根据类型加载样本（自动解析路径 + 明确报错）
        if request.dataset_type == "vqa_v2":
            samples = DatasetLoader.load_vqa_v2_subset(
                data_dir=request.dataset_path or None,
                max_samples=request.max_samples
            )
        elif request.dataset_type == "textvqa":
            samples = DatasetLoader.load_textvqa_subset(
                data_dir=request.dataset_path or None,
                max_samples=request.max_samples
            )
        elif request.dataset_type == "custom":
            if not request.dataset_path:
                raise HTTPException(
                    status_code=400,
                    detail="自定义数据集需要指定 JSON 文件路径。格式参考: data/datasets/sample_custom.json"
                )
            samples = DatasetLoader.load_custom_dataset(request.dataset_path)
        else:
            # builtin: 管线测试（无图片）
            samples = DatasetLoader._get_builtin_test_samples(
                request.image_type, request.max_samples
            )
            logger.warning(
                "⚠️ 使用内置管线测试样本（无图片）。结果不能反映VLM的看图理解能力。"
            )

        if not samples:
            raise HTTPException(status_code=400, detail="No samples loaded. Check dataset path or type.")

        # 为有路径的样本加载 base64 编码
        for sample in samples:
            if sample.image_path and not sample.image_base64 and os.path.exists(sample.image_path):
                with open(sample.image_path, 'rb') as f:
                    sample.image_base64 = base64.b64encode(f.read()).decode('utf-8')

        # 运行评测
        from app.config import settings
        report = await evaluator.evaluate_dataset(
            samples=samples,
            dataset_name=request.dataset_type,
            model_name=settings.model_name,
            max_concurrent=2  # 控制并发避免API限流
        )

        # 同步案例到案例分析器
        case_analyzer.add_from_eval_results(
            success_cases=report.success_cases,
            failure_cases=report.failure_cases
        )

        # 格式化报告文本
        report_text = evaluator.format_report(report)

        return {
            "dataset_name": report.dataset_name,
            "model_name": report.model_name,
            "total_samples": report.total_samples,
            "accuracy": report.accuracy,
            "contains_match_rate": report.contains_match_rate,
            "exact_match_rate": report.exact_match_rate,
            "avg_response_time": report.avg_response_time,
            "correct_count": report.correct_count,
            "error_analysis": report.error_analysis,
            "success_cases": [
                {
                    "id": c.sample_id,
                    "question": c.question,
                    "ground_truth": c.ground_truth,
                    "prediction": c.prediction[:200],
                }
                for c in report.success_cases[:5]
            ],
            "failure_cases": [
                {
                    "id": c.sample_id,
                    "question": c.question,
                    "ground_truth": c.ground_truth,
                    "prediction": c.prediction[:200],
                }
                for c in report.failure_cases[:5]
            ],
            "report_text": report_text
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch evaluation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evaluate/report")
async def get_evaluation_report(
    dataset_type: str = "builtin",
    image_type: str = "natural_scene",
    max_samples: int = 10
):
    """
    快速评测并获取报告（GET方法，方便浏览器调用）
    """
    request = BatchEvalRequest(
        dataset_type=dataset_type,
        image_type=image_type,
        max_samples=max_samples
    )
    return await batch_evaluate(request)


# ==================== 案例分析接口 ====================

@router.post("/cases")
async def add_case(request: CaseAnalysisRequest):
    """添加案例分析"""
    case = case_analyzer.add_case(
        question=request.question,
        prediction=request.prediction,
        ground_truth=request.ground_truth,
        image_type=request.image_type,
        is_success=request.is_success,
        error_type=request.error_type,
        analysis=request.analysis
    )
    return {"message": "Case added", "case_id": case.id}


@router.get("/cases")
async def list_cases():
    """获取所有案例"""
    report = case_analyzer.generate_report()
    return report.to_dict()


@router.get("/cases/report")
async def get_cases_report(format: str = "json"):
    """获取案例分析报告"""
    if format == "markdown":
        content = case_analyzer.export_report_markdown()
        return PlainTextResponse(content, media_type="text/markdown")

    report = case_analyzer.generate_report()
    return report.to_dict()


@router.get("/cases/{case_id}")
async def get_case(case_id: str):
    """获取单个案例详情"""
    case = case_analyzer.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case_analyzer._case_to_dict(case)


@router.put("/cases/{case_id}/analysis")
async def update_case_analysis(case_id: str, analysis: str = Form(...)):
    """更新案例分析"""
    success = case_analyzer.update_analysis(case_id, analysis)
    if not success:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"message": "Analysis updated"}


@router.delete("/cases")
async def clear_cases():
    """清空所有案例"""
    case_analyzer.clear_cases()
    return {"message": "All cases cleared"}


# ==================== 系统提示词模板接口 ====================

SYSTEM_PROMPTS = {
    "natural_scene": """你是一个智能图文问答助手。请根据用户提供的自然场景图片和问题，给出准确、详细的中文回答。
要求：
1. 仔细观察图片中的所有元素（物体、人物、场景、颜色、动作等）
2. 回答要准确、完整，包含具体细节
3. 如果图片中有文字，请识别并引用
4. 可以基于图片内容进行合理的推理""",

    "document": """你是一个专业的文档分析助手。请根据用户提供的文档图片和问题，给出准确、详细的中文回答。
要求：
1. 识别文档中的所有文字内容（标题、正文、表格数据等）
2. 理解文档结构和层次关系
3. 对表格、图表进行准确解读
4. 回答要专业、准确，引用原文关键信息
5. 可以总结、概括文档的主要内容""",

    "slide": """你是一个课件/幻灯片分析助手。请根据用户提供的幻灯片图片和问题，给出准确、详细的中文回答。
要求：
1. 识别幻灯片中的所有文字和图表
2. 理解幻灯片的逻辑结构和要点层次
3. 对图表、示意图进行解读
4. 回答要结构清晰，突出要点
5. 可以补充相关知识点的解释""",

    "product": """你是一个电商商品分析助手。请根据用户提供的商品图片和问题，给出准确、详细的中文回答。
要求：
1. 仔细观察商品的外观、特征、品牌标识等
2. 描述商品的类型、功能、特点
3. 如果图片中有规格参数，请准确识别
4. 可以提供使用建议或对比分析
5. 回答要客观、实用""",

    "general": """你是一个智能图文问答助手。请根据用户提供的图片和问题，给出准确、详细的中文回答。
要求：
1. 仔细观察图片中的所有细节
2. 回答要准确、完整
3. 如果涉及到图片中的文字，请准确识别
4. 可以基于图片内容进行合理的推理和分析
5. 使用清晰流畅的中文表达"""
}


@router.get("/prompts")
async def get_system_prompts():
    """获取所有系统提示词模板"""
    return {
        "prompts": [
            {"type": key, "content": value}
            for key, value in SYSTEM_PROMPTS.items()
        ]
    }


@router.get("/prompts/{prompt_type}")
async def get_system_prompt(prompt_type: str):
    """获取特定类型的系统提示词"""
    if prompt_type not in SYSTEM_PROMPTS:
        raise HTTPException(status_code=404, detail=f"Prompt type '{prompt_type}' not found")
    return {"type": prompt_type, "content": SYSTEM_PROMPTS[prompt_type]}

