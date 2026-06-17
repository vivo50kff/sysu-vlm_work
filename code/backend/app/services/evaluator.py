"""
评测服务模块 - 数据集加载、批量评测、指标计算

数据集目录结构 (data/datasets/):
├── README.md              # 下载与使用说明
├── sample_custom.json     # 自定义数据集格式示例
├── vqa_v2/                # VQA-v2 数据集 (需自行下载)
│   ├── v2_OpenEnded_mscoco_val2014_questions.json
│   ├── v2_mscoco_val2014_annotations.json
│   └── val2014/           # COCO val2014 图片
│       └── COCO_val2014_000000000001.jpg ...
└── textvqa/               # TextVQA 数据集 (需自行下载)
    ├── TextVQA_0.5.1_val_questions.json
    ├── TextVQA_0.5.1_val_annotations.json
    └── val_images/        # TextVQA 图片
        └── 0000001.jpg ...
"""
import json
import os
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from loguru import logger
import asyncio

from app.services.vlm_service import vlm_service


# ============================================================
# 数据集注册表
# ============================================================

# 项目根目录 (backend/ 的上级, 即 code/)
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent  # app/services/ -> app/ -> backend/
_PROJECT_DIR = _BACKEND_DIR.parent  # backend/ -> code/
DATASETS_BASE_DIR = os.path.join(_PROJECT_DIR, "data", "datasets")

DATASET_REGISTRY = {
    "builtin": {
        "key": "builtin",
        "name": "管线测试（无图片）",
        "description": "纯文本问答对，不含任何图片。仅用于验证评测管线是否正常，不能评估VLM的看图理解能力。",
        "has_images": False,
        "standard_path": None,
        "required_files": None,
        "download_url": None,
        "download_size": None,
        "image_types": ["natural_scene", "document"],
        "note": "⚠️ 无图片，不能评估VLM能力"
    },
    "vqa_v2": {
        "key": "vqa_v2",
        "name": "VQA-v2",
        "description": "自然场景图像问答数据集，200K+ 样本，包含开放式问答和多选题。",
        "has_images": True,
        "standard_path": os.path.join(DATASETS_BASE_DIR, "vqa_v2"),
        "required_files": [
            "v2_OpenEnded_mscoco_val2014_questions.json",
            "v2_mscoco_val2014_annotations.json",
            "val2014",  # 图片目录（只需检查目录存在）
        ],
        "download_url": "https://visualqa.org/download.html",
        "download_size": "~6.5 GB (含 COCO val2014 图片)",
        "image_types": ["natural_scene"],
        "note": None
    },
    "textvqa": {
        "key": "textvqa",
        "name": "TextVQA",
        "description": "场景文本问答数据集，专注于图像中文字的理解和推理。45K+ 验证集样本。",
        "has_images": True,
        "standard_path": os.path.join(DATASETS_BASE_DIR, "textvqa"),
        "required_files": [
            "TextVQA_0.5.1_val_questions.json",
            "TextVQA_0.5.1_val_annotations.json",
            "val_images",
        ],
        "download_url": "https://textvqa.org/download/",
        "download_size": "~2 GB",
        "image_types": ["document"],
        "note": None
    },
    "custom": {
        "key": "custom",
        "name": "自定义数据集",
        "description": "用户提供的 JSON 格式数据集，支持任意图片和问题。参考 data/datasets/sample_custom.json 示例。",
        "has_images": True,
        "standard_path": None,  # 用户指定
        "required_files": None,
        "download_url": None,
        "download_size": None,
        "image_types": ["natural_scene", "document", "slide"],
        "note": "需要手动指定 JSON 文件路径"
    },
}


# ============================================================
# 数据模型
# ============================================================

@dataclass
class EvalSample:
    """评测样本"""
    id: str
    image_path: Optional[str] = None
    image_base64: Optional[str] = None
    question: str = ""
    ground_truth: str = ""
    image_type: str = "natural_scene"


@dataclass
class EvalResult:
    """单条评测结果"""
    sample_id: str
    question: str
    ground_truth: str
    prediction: str
    is_correct: bool
    exact_match: bool
    contains_match: bool
    response_time: float = 0.0


@dataclass
class EvalReport:
    """评测报告"""
    dataset_name: str
    model_name: str
    total_samples: int
    correct_count: int
    accuracy: float
    exact_match_count: int
    exact_match_rate: float
    contains_match_count: int
    contains_match_rate: float
    avg_response_time: float
    results: List[EvalResult] = field(default_factory=list)
    error_analysis: Dict = field(default_factory=dict)
    success_cases: List[EvalResult] = field(default_factory=list)
    failure_cases: List[EvalResult] = field(default_factory=list)


# ============================================================
# 数据集加载器
# ============================================================

class DatasetLoader:
    """数据集加载器 — 支持自动检测标准路径"""

    # ---- 可用性检测 ----

    @staticmethod
    def check_dataset_availability() -> Dict:
        """
        检测所有已注册数据集的可用状态。

        Returns:
            {
                "datasets": [{
                    "key": "vqa_v2",
                    "name": "VQA-v2",
                    "available": true/false,
                    "path": "/path/to/dataset" | null,
                    "has_images": true/false,
                    "description": "...",
                    "download_url": "..." | null,
                    "download_size": "..." | null,
                    "image_types": [...],
                    "note": "..." | null,
                    "missing_files": [...] | null  (仅 unavailable 时)
                }, ...],
                "datasets_base_dir": "data/datasets/"
            }
        """
        result = []

        for key, info in DATASET_REGISTRY.items():
            entry = {
                "key": info["key"],
                "name": info["name"],
                "description": info["description"],
                "has_images": info["has_images"],
                "download_url": info["download_url"],
                "download_size": info["download_size"],
                "image_types": info["image_types"],
                "note": info["note"],
                "path": None,
                "available": False,
                "missing_files": None,
            }

            if key in ("builtin",):
                # builtin 始终可用
                entry["available"] = True
                entry["path"] = None
            elif key == "custom":
                # custom 需要用户提供路径，标记为 available（需要手动指定）
                entry["available"] = True
                entry["note"] = "需要手动指定 JSON 文件路径"
            elif info["standard_path"] and info["required_files"]:
                path = info["standard_path"]
                entry["path"] = path
                missing = []
                for f in info["required_files"]:
                    full = os.path.join(path, f)
                    if not os.path.exists(full):
                        missing.append(f)
                entry["available"] = len(missing) == 0
                entry["missing_files"] = missing if missing else None
                if not entry["available"] and missing:
                    entry["note"] = f"缺少: {', '.join(missing[:3])}" + (
                        f" ... 等{len(missing)}项" if len(missing) > 3 else ""
                    )

            result.append(entry)

        return {
            "datasets": result,
            "datasets_base_dir": os.path.relpath(DATASETS_BASE_DIR, _PROJECT_DIR),
        }

    @staticmethod
    def _resolve_dataset_path(dataset_type: str, user_path: Optional[str] = None) -> str:
        """
        解析数据集路径：优先标准路径，其次用户指定。

        Raises:
            FileNotFoundError: 数据集不可用
        """
        if dataset_type in ("builtin",):
            return None

        registry_entry = DATASET_REGISTRY.get(dataset_type)
        if not registry_entry:
            raise ValueError(f"未知数据集类型: {dataset_type}")

        # 1. 尝试标准路径
        std_path = registry_entry.get("standard_path")
        if std_path:
            required = registry_entry.get("required_files")
            if required:
                all_exist = all(os.path.exists(os.path.join(std_path, f)) for f in required)
                if all_exist:
                    logger.info(f"使用标准路径: {std_path}")
                    return std_path

        # 2. 尝试用户指定路径
        if user_path and os.path.isdir(user_path):
            logger.info(f"使用用户指定路径: {user_path}")
            return user_path

        # 3. 不可用 — 给出明确错误
        if dataset_type == "custom":
            raise FileNotFoundError(
                f"自定义数据集文件不存在。请提供一个 JSON 文件路径。\n"
                f"格式参考: data/datasets/sample_custom.json"
            )

        raise FileNotFoundError(
            f"{registry_entry['name']} 数据集不可用。\n"
            f"  - 标准路径: {std_path}\n"
            f"  - 下载地址: {registry_entry['download_url']}\n"
            f"  - 大小: {registry_entry['download_size']}\n"
            f"  - 下载后请解压到标准路径，或在评测时手动指定路径。\n"
            f"  - 也可使用'管线测试(无图片)'快速验证评测管线。"
        )

    # ---- 数据集加载 ----

    @staticmethod
    def load_vqa_v2_subset(data_dir: str = None, max_samples: int = 100) -> List[EvalSample]:
        """加载 VQA-v2 数据集子集。data_dir 为空时自动解析标准路径。"""
        data_dir = DatasetLoader._resolve_dataset_path("vqa_v2", data_dir)

        samples = []
        questions_file = os.path.join(data_dir, "v2_OpenEnded_mscoco_val2014_questions.json")
        annotations_file = os.path.join(data_dir, "v2_mscoco_val2014_annotations.json")

        with open(questions_file, 'r') as f:
            questions_data = json.load(f)
        with open(annotations_file, 'r') as f:
            annotations_data = json.load(f)

        q_dict = {q['question_id']: q['question'] for q in questions_data['questions']}
        a_dict = {a['question_id']: a['multiple_choice_answer'] for a in annotations_data['annotations']}

        question_ids = list(q_dict.keys())[:max_samples]
        for qid in question_ids:
            if qid not in a_dict:
                continue
            img_id = None
            for q in questions_data['questions']:
                if q['question_id'] == qid:
                    img_id = q['image_id']
                    break

            image_filename = f"COCO_val2014_{img_id:012d}.jpg"
            image_path = os.path.join(data_dir, "val2014", image_filename) if img_id else None

            samples.append(EvalSample(
                id=f"vqa_{qid}",
                image_path=image_path,
                question=q_dict[qid],
                ground_truth=a_dict[qid],
                image_type="natural_scene"
            ))

        logger.info(f"Loaded {len(samples)} VQA-v2 samples from {data_dir}")
        return samples

    @staticmethod
    def load_textvqa_subset(data_dir: str = None, max_samples: int = 100) -> List[EvalSample]:
        """加载 TextVQA 数据集子集。data_dir 为空时自动解析标准路径。"""
        data_dir = DatasetLoader._resolve_dataset_path("textvqa", data_dir)

        samples = []
        questions_file = os.path.join(data_dir, "TextVQA_0.5.1_val_questions.json")
        annotations_file = os.path.join(data_dir, "TextVQA_0.5.1_val_annotations.json")

        with open(questions_file, 'r') as f:
            questions_data = json.load(f)
        with open(annotations_file, 'r') as f:
            annotations_data = json.load(f)

        q_dict = {q['question_id']: q['question'] for q in questions_data['questions']}
        a_dict = {a['question_id']: a['answers'] for a in annotations_data['annotations']}

        question_ids = list(q_dict.keys())[:max_samples]
        for qid in question_ids:
            if qid not in a_dict:
                continue
            img_id = None
            for q in questions_data['questions']:
                if q['question_id'] == qid:
                    img_id = q.get('image_id', None)
                    break

            image_path = os.path.join(data_dir, "val_images", f"{img_id}.jpg") if img_id else None
            ground_truth = a_dict[qid][0] if a_dict[qid] else ""

            samples.append(EvalSample(
                id=f"textvqa_{qid}",
                image_path=image_path,
                question=q_dict[qid],
                ground_truth=ground_truth,
                image_type="document"
            ))

        logger.info(f"Loaded {len(samples)} TextVQA samples from {data_dir}")
        return samples

    @staticmethod
    def load_custom_dataset(data_file: str) -> List[EvalSample]:
        """
        加载自定义数据集（JSON 格式）。

        格式参考: data/datasets/sample_custom.json
        """
        samples = []
        data_dir = os.path.dirname(os.path.abspath(data_file))

        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for item in data:
            image_base64 = None
            image_path = item.get("image_path")

            # 相对路径 → 相对于 JSON 文件所在目录
            if image_path:
                if not os.path.isabs(image_path):
                    image_path = os.path.join(data_dir, image_path)
                if os.path.exists(image_path):
                    import base64
                    with open(image_path, 'rb') as img_file:
                        image_base64 = base64.b64encode(img_file.read()).decode('utf-8')

            samples.append(EvalSample(
                id=item.get("id", f"custom_{len(samples)}"),
                image_path=image_path,
                image_base64=image_base64 or item.get("image_base64"),
                question=item["question"],
                ground_truth=item["ground_truth"],
                image_type=item.get("image_type", "natural_scene")
            ))

        logger.info(f"Loaded {len(samples)} custom samples from {data_file}")
        return samples

    @staticmethod
    def _get_builtin_test_samples(image_type: str = "natural_scene", count: int = 10) -> List[EvalSample]:
        """
        ⚠️ 管线测试样本 — 不含任何图片，纯文本问答对。
        仅用于验证评测管线是否正常运行，不能用于评估 VLM 的看图理解能力。

        要评估 VLM 能力，请使用 VQA-v2、TextVQA 或自定义数据集。
        """
        test_samples = {
            "natural_scene": [
                (f"test_scene_{i}", q, a)
                for i, (q, a) in enumerate([
                    ("图片中有什么动物？", "猫"),
                    ("这是什么颜色的？", "红色"),
                    ("图中有几个人？", "两个人"),
                    ("这是在室内还是室外？", "室外"),
                    ("现在是什么天气？", "晴天"),
                    ("图中有什么植物？", "树"),
                    ("这是什么交通工具？", "汽车"),
                    ("图片中的食物是什么？", "苹果"),
                    ("这个建筑是什么风格？", "现代"),
                    ("图中人物在做什么？", "跑步"),
                ])
            ],
            "document": [
                (f"test_doc_{i}", q, a)
                for i, (q, a) in enumerate([
                    ("文档的标题是什么？", "年度报告"),
                    ("表格中有几行数据？", "5行"),
                    ("文档中提到了哪个日期？", "2024年1月"),
                    ("图表显示的趋势是什么？", "增长趋势"),
                    ("文档的作者是谁？", "张三"),
                    ("这段话的主要观点是什么？", "人工智能的重要性"),
                    ("文档中有几个章节？", "三个章节"),
                    ("图表中的最大值是多少？", "100"),
                    ("文档的关键词有哪些？", "AI, 深度学习, 多模态"),
                    ("这个公式是什么？", "E=mc²"),
                ])
            ],
        }

        items = test_samples.get(image_type, test_samples["natural_scene"])[:count]
        return [
            EvalSample(
                id=item[0],
                question=item[1],
                ground_truth=item[2],
                image_type=image_type
            )
            for item in items
        ]


# ============================================================
# 评测指标
# ============================================================

class MetricsCalculator:
    """指标计算器"""

    @staticmethod
    def exact_match(prediction: str, ground_truth: str) -> bool:
        """精确匹配"""
        return prediction.strip().lower() == ground_truth.strip().lower()

    @staticmethod
    def contains_match(prediction: str, ground_truth: str) -> bool:
        """包含匹配（预测中包含标准答案，或标准答案包含预测）"""
        pred = prediction.strip().lower()
        gt = ground_truth.strip().lower()
        return gt in pred or pred in gt

    @staticmethod
    def fuzzy_match(prediction: str, ground_truth: str, threshold: float = 0.6) -> bool:
        """模糊匹配（基于字符重叠率）"""
        pred_chars = set(prediction.strip().lower())
        gt_chars = set(ground_truth.strip().lower())
        if not gt_chars:
            return False
        return len(pred_chars & gt_chars) / len(gt_chars) >= threshold

    @staticmethod
    def calculate_accuracy(results: List[EvalResult], match_type: str = "contains") -> float:
        """计算准确率"""
        if not results:
            return 0.0
        if match_type == "exact":
            return sum(1 for r in results if r.exact_match) / len(results)
        elif match_type == "contains":
            return sum(1 for r in results if r.contains_match) / len(results)
        return sum(1 for r in results if r.is_correct) / len(results)

    @staticmethod
    def classify_error(prediction: str, ground_truth: str, question: str) -> str:
        """分类错误类型"""
        pred = prediction.strip().lower()
        gt = ground_truth.strip().lower()

        has_numbers = any(c.isdigit() for c in gt)
        has_english = any(c.isascii() and c.isalpha() for c in gt)

        if not pred:
            return "empty_response"
        elif has_numbers and any(c.isdigit() for c in pred):
            return "ocr_error"
        elif has_english:
            return "text_recognition_error"
        elif len(pred) < len(gt) * 0.3:
            return "incomplete_answer"
        elif len(pred) > len(gt) * 3:
            return "overly_verbose"
        elif any(word in pred for word in ["无法", "不清楚", "不确定", "抱歉"]):
            return "model_refusal"
        elif any(gt_word in pred for gt_word in gt.split() if len(gt_word) > 1):
            return "partial_match"
        else:
            return "content_mismatch"


# ============================================================
# VQA 评测器
# ============================================================

class VQAEvaluator:
    """VQA评测器"""

    def __init__(self):
        self.metrics = MetricsCalculator()

    async def evaluate_sample(self, sample: EvalSample) -> EvalResult:
        """评测单个样本"""
        start_time = time.time()

        try:
            prediction = await vlm_service.chat(
                message=sample.question,
                image_base64=sample.image_base64,
                history=None
            )
        except Exception as e:
            logger.error(f"Error evaluating sample {sample.id}: {e}")
            prediction = f"[ERROR: {str(e)}]"

        response_time = time.time() - start_time
        exact = self.metrics.exact_match(prediction, sample.ground_truth)
        contains = self.metrics.contains_match(prediction, sample.ground_truth)

        return EvalResult(
            sample_id=sample.id,
            question=sample.question,
            ground_truth=sample.ground_truth,
            prediction=prediction,
            is_correct=contains or exact,
            exact_match=exact,
            contains_match=contains,
            response_time=response_time
        )

    async def evaluate_dataset(
        self,
        samples: List[EvalSample],
        dataset_name: str = "unknown",
        model_name: str = "qwen-vl-plus",
        max_concurrent: int = 3,
        progress_callback=None
    ) -> EvalReport:
        """批量评测数据集"""
        results: List[EvalResult] = []
        total = len(samples)

        for i in range(0, total, max_concurrent):
            batch = samples[i:i + max_concurrent]
            tasks = [self.evaluate_sample(s) for s in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Batch error: {result}")
                    results.append(EvalResult(
                        sample_id=batch[j].id,
                        question=batch[j].question,
                        ground_truth=batch[j].ground_truth,
                        prediction=f"[ERROR: {str(result)}]",
                        is_correct=False,
                        exact_match=False,
                        contains_match=False
                    ))
                else:
                    results.append(result)

            if progress_callback:
                progress_callback(min(i + max_concurrent, total), total)

            logger.info(f"Evaluated {min(i + max_concurrent, total)}/{total} samples")

        correct_count = sum(1 for r in results if r.is_correct)
        exact_count = sum(1 for r in results if r.exact_match)
        contains_count = sum(1 for r in results if r.contains_match)
        avg_time = sum(r.response_time for r in results) / len(results) if results else 0

        success_cases = [r for r in results if r.is_correct]
        failure_cases = [r for r in results if not r.is_correct]

        error_types = {}
        for r in failure_cases:
            error_type = self.metrics.classify_error(r.prediction, r.ground_truth, r.question)
            error_types[error_type] = error_types.get(error_type, 0) + 1

        return EvalReport(
            dataset_name=dataset_name,
            model_name=model_name,
            total_samples=total,
            correct_count=correct_count,
            accuracy=correct_count / total if total > 0 else 0,
            exact_match_count=exact_count,
            exact_match_rate=exact_count / total if total > 0 else 0,
            contains_match_count=contains_count,
            contains_match_rate=contains_count / total if total > 0 else 0,
            avg_response_time=avg_time,
            results=results,
            error_analysis={
                "error_types": error_types,
                "total_errors": len(failure_cases),
                "error_rate": len(failure_cases) / total if total > 0 else 0
            },
            success_cases=success_cases[:10],
            failure_cases=failure_cases[:10]
        )

    @staticmethod
    def format_report(report: EvalReport) -> str:
        """格式化评测报告为文本"""
        type_names = {
            "empty_response": "空响应", "ocr_error": "OCR识别错误",
            "text_recognition_error": "文本识别错误", "incomplete_answer": "回答不完整",
            "overly_verbose": "回答过于冗长", "model_refusal": "模型拒答",
            "partial_match": "部分匹配", "content_mismatch": "内容不匹配"
        }

        lines = [
            "=" * 60,
            f"📊 评测报告: {report.dataset_name}",
            "=" * 60,
            f"模型: {report.model_name}",
            f"样本总数: {report.total_samples}",
            "",
            "--- 准确率指标 ---",
            f"✅ 包含匹配准确率: {report.contains_match_rate:.2%} ({report.contains_match_count}/{report.total_samples})",
            f"🎯 精确匹配准确率: {report.exact_match_rate:.2%} ({report.exact_match_count}/{report.total_samples})",
            f"📈 综合准确率: {report.accuracy:.2%} ({report.correct_count}/{report.total_samples})",
            f"⏱️  平均响应时间: {report.avg_response_time:.2f}秒",
            "",
            "--- 错误分析 ---",
            f"错误总数: {report.error_analysis.get('total_errors', 0)}",
            f"错误率: {report.error_analysis.get('error_rate', 0):.2%}",
            "", "错误类型分布:",
        ]
        for error_type, count in report.error_analysis.get("error_types", {}).items():
            lines.append(f"  - {type_names.get(error_type, error_type)}: {count}次")

        lines.extend(["", "--- 成功案例 (前5个) ---"])
        for i, case in enumerate(report.success_cases[:5]):
            lines.extend([f"  [{i+1}] Q: {case.question}", f"      GT: {case.ground_truth}",
                          f"      Pred: {case.prediction[:100]}", ""])

        lines.extend(["", "--- 失败案例 (前5个) ---"])
        for i, case in enumerate(report.failure_cases[:5]):
            lines.extend([f"  [{i+1}] Q: {case.question}", f"      GT: {case.ground_truth}",
                          f"      Pred: {case.prediction[:100]}", ""])

        lines.append("=" * 60)
        return "\n".join(lines)


# 全局评测器实例
evaluator = VQAEvaluator()
