#!/usr/bin/env python3
"""
VLM图文问答助手 - 命令行交互界面 (CLI)
用法:
  交互式对话:  python cli.py
  批量评测:    python cli.py --eval --samples 20
  指定API:     python cli.py --api http://localhost:8000/api/v1

依赖: httpx (pip install httpx)
可选: rich   (pip install rich，提供彩色输出；没有也能用)
"""
import asyncio
import base64
import os
import argparse
import json
from typing import Optional, Dict

import httpx

# ── 可选依赖: rich ──────────────────────────────────────────
try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.table import Table
    from rich.prompt import Prompt
    RICH_OK = True
except ImportError:
    RICH_OK = False


# ── 简单的纯文本控制台（无 rich 时使用） ─────────────────────
class PlainConsole:
    """rich 的简单替代，不依赖第三方库"""
    def print(self, *args, **kwargs):
        print(*args)

    def input(self, prompt=""):
        return input(prompt)

    @staticmethod
    def clear():
        os.system('clear' if os.name != 'nt' else 'cls')


console = Console() if RICH_OK else PlainConsole()
_HAS_RICH = RICH_OK


# ── 颜色辅助 ────────────────────────────────────────────────
def green(s):  return f"\033[32m{s}\033[0m"
def red(s):    return f"\033[31m{s}\033[0m"
def yellow(s): return f"\033[33m{s}\033[0m"
def cyan(s):   return f"\033[36m{s}\033[0m"
def bold(s):   return f"\033[1m{s}\033[0m"
def dim(s):    return f"\033[2m{s}\033[0m"


# ── CLI 主类 ────────────────────────────────────────────────

class VLMCLI:
    """VLM图文问答助手 命令行客户端"""

    IMAGE_TYPES = ["natural_scene", "document", "slide", "product"]
    IMAGE_TYPE_LABELS = {
        "natural_scene": "🌄 自然场景",
        "document": "📄 文档",
        "slide": "📊 幻灯片",
        "product": "🛍️ 商品",
    }

    def __init__(self, api_url: str = "http://localhost:8000/api/v1"):
        self.api_url = api_url.rstrip("/")
        self.conversation_id: Optional[str] = None
        self.image_type: str = "natural_scene"
        self.client = httpx.AsyncClient(timeout=120.0)
        # 项目根目录: cli.py 在 code/ 下，其上级即项目根
        self.project_root = os.path.dirname(os.path.abspath(__file__))

    # ── API 调用 ──────────────────────────────────────────

    async def health_check(self) -> bool:
        """检查 API 连接"""
        try:
            resp = await self.client.get(f"{self.api_url}/health")
            if resp.status_code == 200:
                data = resp.json()
                print(f"{green('✅')} 已连接到 {bold(data['api_provider'])} ({data['model_name']})")
                return True
            print(f"{red('❌')} API 不可用: HTTP {resp.status_code}")
            return False
        except Exception as e:
            print(f"{red('❌')} 无法连接到 {self.api_url}: {e}")
            print(f"   请确保后端已启动: bash scripts/start.sh")
            return False

    async def send_message(self, message: str, image_path: Optional[str] = None) -> str:
        """发送消息，返回 AI 回复"""
        image_base64 = None
        if image_path:
            resolved = self._resolve_image_path(image_path)
            if resolved:
                with open(resolved, 'rb') as f:
                    image_base64 = base64.b64encode(f.read()).decode('utf-8')
                print(dim(f"📷 已加载图片: {resolved}"))
            else:
                # 列出尝试过的路径
                tried = [os.path.expanduser(image_path),
                         os.path.join(self.project_root, image_path)]
                tried = [p for p in tried if p != image_path or True]  # dedup later
                print(f"{red('❌')} 图片不存在: {image_path}")
                print(dim(f"   尝试过: {', '.join(set(tried))}"))
                return ""

        try:
            resp = await self.client.post(
                f"{self.api_url}/chat",
                json={
                    "message": message,
                    "image_base64": image_base64,
                    "conversation_id": self.conversation_id,
                    "image_type": self.image_type,
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                self.conversation_id = data["conversation_id"]
                return data["response"]
            else:
                detail = resp.json().get("detail", resp.text)
                print(f"{red('❌')} API 错误 ({resp.status_code}): {detail[:300]}")
                return ""
        except Exception as e:
            print(f"{red('❌')} 请求失败: {e}")
            return ""

    # ── 评测 ──────────────────────────────────────────────

    async def run_batch_eval(self, dataset_type: str, image_type: str, count: int,
                             dataset_path: Optional[str] = None):
        """运行批量评测"""
        payload = {"dataset_type": dataset_type, "image_type": image_type,
                    "max_samples": count}
        if dataset_path:
            payload["dataset_path"] = dataset_path

        print(cyan("📊 正在评测..."))
        try:
            resp = await self.client.post(f"{self.api_url}/evaluate/batch", json=payload)
            if resp.status_code == 200:
                self._print_eval_report(resp.json())
            else:
                detail = resp.json().get("detail", resp.text)
                print(f"{red('❌')} 评测失败: {detail[:500]}")
        except Exception as e:
            print(f"{red('❌')} 评测错误: {e}")

    def _print_eval_report(self, data: Dict):
        """打印评测报告"""
        if _HAS_RICH:
            table = Table(title=f"📊 评测报告 - {data.get('dataset_name', '')}")
            table.add_column("指标", style="cyan")
            table.add_column("数值", style="green")
            rows = [
                ("模型", data.get("model_name", "")),
                ("样本总数", str(data.get("total_samples", 0))),
                ("正确数", str(data.get("correct_count", 0))),
                ("综合准确率", f"{data.get('accuracy', 0):.1%}"),
                ("包含匹配率", f"{data.get('contains_match_rate', 0):.1%}"),
                ("精确匹配率", f"{data.get('exact_match_rate', 0):.1%}"),
                ("平均耗时", f"{data.get('avg_response_time', 0):.2f}秒"),
            ]
            for label, value in rows:
                table.add_row(label, value)
            console.print(table)
        else:
            print(f"\n{'='*50}")
            print(f"📊 评测报告 - {data.get('dataset_name', '')}")
            print(f"{'='*50}")
            print(f"  模型: {data.get('model_name', '')}")
            print(f"  样本数: {data.get('total_samples', 0)}, 正确: {data.get('correct_count', 0)}")
            print(f"  综合准确率: {data.get('accuracy', 0):.1%}")
            print(f"  包含匹配率: {data.get('contains_match_rate', 0):.1%}")
            print(f"  精确匹配率: {data.get('exact_match_rate', 0):.1%}")
            print(f"  平均耗时: {data.get('avg_response_time', 0):.2f}秒")

        # 成功/失败案例摘要
        for label, key, color in [("✅ 成功案例", "success_cases", green),
                                   ("❌ 失败案例", "failure_cases", red)]:
            cases = data.get(key, [])
            if cases:
                print(f"\n{label} (前3个):")
                for c in cases[:3]:
                    print(f"  Q: {c['question']}")
                    if key == "failure_cases":
                        print(f"  GT: {c.get('ground_truth', '')}")
                    print(f"  A: {c.get('prediction', '')[:120]}")

    # ── 交互循环 ──────────────────────────────────────────

    async def chat_loop(self):
        """交互式对话主循环"""
        if _HAS_RICH:
            console.clear()
            console.print(Panel.fit(
                "[bold cyan]🤖 VLM图文问答助手 - 命令行版[/bold cyan]\n"
                "[dim]基于视觉语言模型的智能图文问答系统[/dim]",
                border_style="cyan"
            ))
        else:
            PlainConsole.clear()
            print(bold("🤖 VLM图文问答助手 - 命令行版"))
            print(dim("基于视觉语言模型的智能图文问答系统"))
            print()

        self._print_shortcuts()

        while True:
            try:
                user_input = self._get_input()

                if not user_input.strip():
                    continue

                cmd = user_input.strip().lower()

                # ── 内置命令 ──
                if cmd in ('exit', 'quit', 'q'):
                    print(yellow("再见！"))
                    break

                if cmd == 'clear':
                    self.conversation_id = None
                    print(green("对话已清空"))
                    continue

                if cmd == 'help':
                    self._show_help()
                    continue

                if cmd == 'shortcuts':
                    self._print_shortcuts()
                    continue

                # ── 切换图像类型: /type document ──
                if cmd.startswith('/type ') or cmd.startswith('/t '):
                    parts = user_input.strip().split(maxsplit=1)
                    if len(parts) > 1:
                        t = parts[1].strip()
                        if t in self.IMAGE_TYPES:
                            self.image_type = t
                            print(green(f"已切换到: {self.IMAGE_TYPE_LABELS.get(t, t)}"))
                        else:
                            print(f"{red('❌')} 未知类型: {t}")
                            print(f"   可选: {', '.join(self.IMAGE_TYPES)}")
                    continue

                # ── 显示当前类型: /type ──
                if cmd == '/type' or cmd == '/t':
                    print(f"当前图像类型: {self.IMAGE_TYPE_LABELS.get(self.image_type, self.image_type)}")
                    continue

                # ── 图片问答: /img path 问题 ──
                if cmd.startswith('/img '):
                    rest = user_input.strip()[5:].strip()
                    # 支持引号括起路径: /img "path with spaces" 问题
                    image_path, message = self._parse_img_cmd(rest)
                    if image_path:
                        print(dim("思考中..."))
                        response = await self.send_message(message, image_path)
                        self._print_response(response)
                    continue

                # ── 批量评测: /eval natural_scene 10 ──
                if cmd.startswith('/eval'):
                    parts = user_input.strip().split()
                    dtype = parts[1] if len(parts) > 1 else "builtin"
                    itype = parts[2] if len(parts) > 2 else "natural_scene"
                    cnt = int(parts[3]) if len(parts) > 3 else 10
                    await self.run_batch_eval(dtype, itype, cnt)
                    continue

                # ── 普通消息 ──
                print(dim("思考中..."))
                response = await self.send_message(user_input.strip())
                self._print_response(response)

            except KeyboardInterrupt:
                print(f"\n{yellow('对话结束')}")
                break
            except Exception as e:
                print(f"{red('❌')} 错误: {e}")

    def _print_response(self, response: str):
        if not response:
            return
        if _HAS_RICH:
            console.print(f"\n{bold(green('🤖 助手'))}")
            console.print(Markdown(response))
        else:
            print(f"\n{bold(green('🤖 助手'))}")
            print(response)

    def _get_input(self) -> str:
        """获取用户输入"""
        type_tag = self.IMAGE_TYPE_LABELS.get(self.image_type, self.image_type)
        prompt = f"\n{bold('👤 你')} [{dim(type_tag)}] "
        if _HAS_RICH:
            return Prompt.ask(prompt)
        else:
            return input(prompt)

    @staticmethod
    def _parse_img_cmd(rest: str):
        """解析 /img 命令参数，支持引号括起的路径"""
        rest = rest.strip()
        if rest.startswith('"'):
            end = rest.find('"', 1)
            if end > 0:
                path = rest[1:end]
                msg = rest[end+1:].strip()
                return path, msg or "请描述这张图片"
        if rest.startswith("'"):
            end = rest.find("'", 1)
            if end > 0:
                path = rest[1:end]
                msg = rest[end+1:].strip()
                return path, msg or "请描述这张图片"
        # 无引号：第一个空格前是路径
        parts = rest.split(maxsplit=1)
        path = parts[0]
        msg = parts[1] if len(parts) > 1 else "请描述这张图片"
        return path, msg

    def _resolve_image_path(self, image_path: str) -> Optional[str]:
        """
        智能解析图片路径。按顺序尝试：
        1. 原路径（支持 ~ 展开和绝对路径）
        2. 相对于项目根目录（code/）
        3. 相对于当前工作目录
        """
        # 展开 ~
        expanded = os.path.expanduser(image_path)
        if os.path.isabs(expanded) and os.path.exists(expanded):
            return expanded

        # 相对路径：依次尝试多个基准目录
        search_dirs = [
            os.getcwd(),            # 当前工作目录
            self.project_root,      # code/（cli.py 所在目录）
            os.path.dirname(self.project_root),  # 项目根目录（code 的上级）
        ]
        for base in search_dirs:
            candidate = os.path.join(base, expanded)
            if os.path.exists(candidate):
                return candidate

        return None

    def _print_shortcuts(self):
        """打印快捷操作提示"""
        lines = [
            f"  {cyan('/img <路径> <问题>')}  {dim('发送图片+问题')}",
            f"  {cyan('/type <类型>')}        {dim('切换图像类型')}  "
            f"{dim('可选: ' + ', '.join(self.IMAGE_TYPES))}",
            f"  {cyan('/eval <数据集> <类型> <数量>')}  {dim('批量评测')}",
            f"  {cyan('clear / exit / help')}       {dim('对话管理')}",
        ]
        print(dim("━" * 55))
        for line in lines:
            print(line)
        print(f"  {dim(f'当前模式: {self.IMAGE_TYPE_LABELS.get(self.image_type, self.image_type)}')}")
        print(dim("━" * 55))

    def _show_help(self):
        """显示帮助"""
        help_text = f"""
{bold(cyan('VLM图文问答助手 - 帮助'))}

{bold('基本使用')}
  直接输入问题，按回车发送。
  文本问题不需要图片也能回答。

{bold('图片问答')}
  {yellow('/img <图片路径> <问题>')}
  示例: /img ~/Desktop/photo.jpg 图中有什么？
        /img "我的图片.jpg" 请描述这张图

{bold('切换模式')}
  {yellow('/type <类型>')}
  可选: natural_scene (自然场景) / document (文档) /
        slide (幻灯片) / product (商品)
  切换后会改变 AI 的回答风格和关注点。

{bold('批量评测')}
  {yellow('/eval <数据集> <图像类型> <数量>')}
  示例: /eval builtin natural_scene 10
        /eval vqa_v2 natural_scene 20

{bold('其他命令')}
  {yellow('clear')}    清空对话
  {yellow('exit')}     退出
  {yellow('help')}     显示帮助
  {yellow('/type')}    查看当前模式
        """
        if _HAS_RICH:
            console.print(Markdown(help_text))
        else:
            print(help_text)

    async def close(self):
        await self.client.aclose()


# ── 评测脚本（命令行 --eval 模式） ──────────────────────────

async def run_evaluation(api_url: str, dataset_type: str, image_type: str,
                          max_samples: int, dataset_path: Optional[str] = None,
                          output_file: Optional[str] = None):
    """运行批量评测并可选保存报告"""
    api_url = api_url.rstrip("/")
    payload = {"dataset_type": dataset_type, "image_type": image_type,
                "max_samples": max_samples}
    if dataset_path:
        payload["dataset_path"] = dataset_path

    print(cyan(f"📊 评测: {dataset_type} × {image_type} × {max_samples}样本"))
    print(f"   API: {api_url}")

    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            resp = await client.post(f"{api_url}/evaluate/batch", json=payload)
            if resp.status_code != 200:
                detail = resp.json().get("detail", resp.text)
                print(f"{red('❌')} 评测失败: {detail[:500]}")
                return

            data = resp.json()

            # 打印报告文本
            report_text = data.get("report_text", "")
            if report_text:
                print(report_text)

            # 保存 JSON
            if output_file:
                out = output_file if output_file.endswith('.json') else output_file + '.json'
                with open(out, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(green(f"✅ 报告已保存: {out}"))

                # 同时保存案例 Markdown
                md_file = out.replace('.json', '_cases.md')
                resp2 = await client.get(f"{api_url}/cases/report?format=markdown")
                if resp2.status_code == 200:
                    with open(md_file, 'w', encoding='utf-8') as f:
                        f.write(resp2.text)
                    print(green(f"✅ 案例报告: {md_file}"))

        except Exception as e:
            print(f"{red('❌')} 错误: {e}")


# ── 入口 ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="VLM图文问答助手 - 命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python cli.py                                        交互式对话
  python cli.py --eval --samples 20                    批量评测
  python cli.py --eval --dataset vqa_v2 --samples 50   指定数据集
  python cli.py --eval --output report.json            保存报告
  python cli.py --api http://localhost:8000/api/v1     指定 API
        """
    )
    parser.add_argument("--api", default="http://localhost:8000/api/v1", help="后端 API 地址")
    parser.add_argument("--eval", action="store_true", help="运行评测模式（非交互）")
    parser.add_argument("--dataset", default="builtin",
                        choices=["builtin", "vqa_v2", "textvqa", "custom"], help="数据集类型")
    parser.add_argument("--image-type", default="natural_scene",
                        choices=["natural_scene", "document", "slide"], help="图像类型")
    parser.add_argument("--samples", type=int, default=10, help="评测样本数")
    parser.add_argument("--dataset-path", help="自定义数据集路径")
    parser.add_argument("--output", help="评测报告输出文件 (.json)")

    args = parser.parse_args()

    async def run():
        if args.eval:
            await run_evaluation(
                api_url=args.api,
                dataset_type=args.dataset,
                image_type=args.image_type,
                max_samples=args.samples,
                dataset_path=args.dataset_path,
                output_file=args.output,
            )
        else:
            cli = VLMCLI(api_url=args.api)
            if await cli.health_check():
                await cli.chat_loop()
            await cli.close()

    asyncio.run(run())


if __name__ == "__main__":
    main()
