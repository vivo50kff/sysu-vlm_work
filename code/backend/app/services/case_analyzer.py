"""
案例分析模块 - 收集、存储、分析成功/失败案例
"""
import json
import os
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from loguru import logger


@dataclass
class CaseRecord:
    """案例记录"""
    id: str
    image_type: str  # natural_scene / document / slide
    question: str
    ground_truth: Optional[str] = None
    prediction: str = ""
    is_success: bool = True
    error_type: Optional[str] = None  # 错误类型（仅失败案例）
    analysis: str = ""  # 人工分析
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    conversation_context: Optional[List[Dict]] = None  # 对话上下文


@dataclass
class CaseAnalysisReport:
    """案例分析报告"""
    total_cases: int
    success_count: int
    failure_count: int
    success_rate: float
    error_type_distribution: Dict[str, int]
    cases: List[CaseRecord]

    def to_dict(self) -> Dict:
        return {
            "total_cases": self.total_cases,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_rate,
            "error_type_distribution": self.error_type_distribution,
            "cases": [
                {
                    "id": c.id,
                    "image_type": c.image_type,
                    "question": c.question,
                    "ground_truth": c.ground_truth,
                    "prediction": c.prediction[:200],
                    "is_success": c.is_success,
                    "error_type": c.error_type,
                    "analysis": c.analysis,
                    "timestamp": c.timestamp
                }
                for c in self.cases
            ]
        }


class CaseAnalyzer:
    """案例分析器"""

    def __init__(self, storage_dir: str = "data/cases"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._cases_file = self.storage_dir / "cases.json"
        self._cases: List[CaseRecord] = []
        self._load_cases()

    def _load_cases(self):
        """从文件加载案例"""
        if self._cases_file.exists():
            try:
                with open(self._cases_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._cases = [
                    CaseRecord(**item) for item in data
                ]
                logger.info(f"Loaded {len(self._cases)} cases from {self._cases_file}")
            except Exception as e:
                logger.error(f"Error loading cases: {e}")
                self._cases = []

    def _save_cases(self):
        """保存案例到文件"""
        try:
            with open(self._cases_file, 'w', encoding='utf-8') as f:
                json.dump(
                    [self._case_to_dict(c) for c in self._cases],
                    f,
                    ensure_ascii=False,
                    indent=2
                )
            logger.info(f"Saved {len(self._cases)} cases to {self._cases_file}")
        except Exception as e:
            logger.error(f"Error saving cases: {e}")

    @staticmethod
    def _case_to_dict(case: CaseRecord) -> Dict:
        return {
            "id": case.id,
            "image_type": case.image_type,
            "question": case.question,
            "ground_truth": case.ground_truth,
            "prediction": case.prediction,
            "is_success": case.is_success,
            "error_type": case.error_type,
            "analysis": case.analysis,
            "timestamp": case.timestamp,
            "conversation_context": case.conversation_context
        }

    def add_case(
        self,
        question: str,
        prediction: str,
        ground_truth: Optional[str] = None,
        image_type: str = "natural_scene",
        is_success: bool = True,
        error_type: Optional[str] = None,
        analysis: str = "",
        conversation_context: Optional[List[Dict]] = None
    ) -> CaseRecord:
        """添加案例"""
        case_id = f"case_{len(self._cases) + 1:04d}"
        case = CaseRecord(
            id=case_id,
            image_type=image_type,
            question=question,
            ground_truth=ground_truth,
            prediction=prediction,
            is_success=is_success,
            error_type=error_type,
            analysis=analysis,
            conversation_context=conversation_context
        )
        self._cases.append(case)
        self._save_cases()
        return case

    def add_from_eval_results(
        self,
        success_cases: List,
        failure_cases: List,
        error_type_map: Optional[Dict[str, str]] = None
    ):
        """从评测结果批量添加案例"""
        for case in success_cases[:10]:
            self.add_case(
                question=case.question,
                prediction=case.prediction,
                ground_truth=case.ground_truth,
                is_success=True
            )

        for case in failure_cases[:10]:
            error_type = error_type_map.get(case.sample_id, "content_mismatch") if error_type_map else "content_mismatch"
            self.add_case(
                question=case.question,
                prediction=case.prediction,
                ground_truth=case.ground_truth,
                is_success=False,
                error_type=error_type
            )

    def get_case(self, case_id: str) -> Optional[CaseRecord]:
        """获取单个案例"""
        for case in self._cases:
            if case.id == case_id:
                return case
        return None

    def update_analysis(self, case_id: str, analysis: str) -> bool:
        """更新案例分析"""
        case = self.get_case(case_id)
        if case:
            case.analysis = analysis
            self._save_cases()
            return True
        return False

    def generate_report(self) -> CaseAnalysisReport:
        """生成案例分析报告"""
        success = [c for c in self._cases if c.is_success]
        failure = [c for c in self._cases if not c.is_success]

        error_types = {}
        for c in failure:
            et = c.error_type or "unknown"
            error_types[et] = error_types.get(et, 0) + 1

        return CaseAnalysisReport(
            total_cases=len(self._cases),
            success_count=len(success),
            failure_count=len(failure),
            success_rate=len(success) / len(self._cases) if self._cases else 0,
            error_type_distribution=error_types,
            cases=self._cases
        )

    def export_report_markdown(self) -> str:
        """导出Markdown格式的分析报告"""
        report = self.generate_report()

        lines = [
            f"# 案例分析报告",
            f"",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"## 概览",
            f"",
            f"| 指标 | 数值 |",
            f"|------|------|",
            f"| 总案例数 | {report.total_cases} |",
            f"| 成功案例 | {report.success_count} |",
            f"| 失败案例 | {report.failure_count} |",
            f"| 成功率 | {report.success_rate:.1%} |",
            f"",
            f"## 错误类型分布",
            f"",
            f"| 错误类型 | 数量 | 占比 |",
            f"|----------|------|------|",
        ]

        error_names = {
            "empty_response": "空响应",
            "ocr_error": "OCR识别错误",
            "text_recognition_error": "文本识别错误",
            "incomplete_answer": "回答不完整",
            "overly_verbose": "回答过于冗长",
            "model_refusal": "模型拒答",
            "partial_match": "部分匹配",
            "content_mismatch": "内容不匹配",
            "unknown": "未知错误"
        }

        for error_type, count in report.error_type_distribution.items():
            pct = count / report.failure_count if report.failure_count > 0 else 0
            lines.append(f"| {error_names.get(error_type, error_type)} | {count} | {pct:.1%} |")

        lines.append("")
        lines.append("## 成功案例")
        lines.append("")

        for i, case in enumerate(report.cases):
            if case.is_success:
                lines.append(f"### 成功案例 {i+1}: {case.id}")
                lines.append(f"- **图像类型**: {case.image_type}")
                lines.append(f"- **问题**: {case.question}")
                lines.append(f"- **标准答案**: {case.ground_truth or 'N/A'}")
                lines.append(f"- **模型预测**: {case.prediction[:200]}")
                if case.analysis:
                    lines.append(f"- **分析**: {case.analysis}")
                lines.append("")

        lines.append("## 失败案例")
        lines.append("")

        for i, case in enumerate(report.cases):
            if not case.is_success:
                lines.append(f"### 失败案例 {i+1}: {case.id}")
                lines.append(f"- **图像类型**: {case.image_type}")
                lines.append(f"- **问题**: {case.question}")
                lines.append(f"- **标准答案**: {case.ground_truth or 'N/A'}")
                lines.append(f"- **模型预测**: {case.prediction[:200]}")
                lines.append(f"- **错误类型**: {error_names.get(case.error_type or 'unknown', '未知')}")
                if case.analysis:
                    lines.append(f"- **分析**: {case.analysis}")
                lines.append("")

        return "\n".join(lines)

    def clear_cases(self):
        """清空所有案例"""
        self._cases = []
        self._save_cases()

    @property
    def case_count(self) -> int:
        return len(self._cases)


# 全局案例分析器实例
case_analyzer = CaseAnalyzer()
