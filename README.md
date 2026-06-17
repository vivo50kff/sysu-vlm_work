# 🤖 VLM图文问答助手

基于视觉语言模型（Vision-Language Model）的智能图文问答系统，支持图片理解、多轮对话、批量评测和案例分析。

## 项目结构

```
code/
├── scripts/                     # 初始化和启动脚本
│   ├── setup.sh / setup.bat     # 环境初始化（安装依赖）
│   └── start.sh / start.bat     # 一键启动服务
│
├── backend/                     # 后端服务 (FastAPI)
│   ├── app/
│   │   ├── api/routes.py        # 全部 API 路由
│   │   ├── services/
│   │   │   ├── vlm_service.py          # VLM API 服务（Qwen/GLM-4V + 系统提示词）
│   │   │   ├── conversation_manager.py # 对话管理（持久化 + 导出/搜索）
│   │   │   ├── evaluator.py           # 评测模块（数据集加载 + 批量评测）
│   │   │   └── case_analyzer.py       # 案例分析模块（收集/分析/报告）
│   │   ├── models.py           # 数据模型
│   │   ├── config.py           # 配置管理
│   │   └── main.py             # 应用入口
│   ├── requirements.txt        # Python 依赖
│   └── .env.example            # 环境变量模板
│
├── frontend/                    # 前端应用 (Vue 3 + Element Plus)
│   ├── src/
│   │   ├── App.vue             # 主组件（聊天 + 侧边栏 + 评测对话框）
│   │   ├── api.js              # 完整 API 客户端
│   │   └── style.css           # 样式
│   └── package.json
│
├── data/
│   └── datasets/               # 标准数据集目录（见下方说明）
│       ├── README.md           # 数据集下载与使用说明
│       └── sample_custom.json  # 自定义数据集格式示例
│
└── cli.py                      # 命令行交互工具
```

## 功能特性

### 核心功能
- ✅ **图文问答** — 上传图片 + 输入问题，AI 智能回答
- ✅ **多轮对话** — 支持上下文关联的连续对话
- ✅ **图像类型切换** — 支持 自然场景 / 文档 / 幻灯片 / 商品 四种模式，**每种模式注入不同的系统提示词**，改变模型回答风格和关注点
- ✅ **对话持久化** — 对话自动保存到 JSON 文件，重启不丢失
- ✅ **对话导出** — 支持导出为 JSON / Markdown 格式
- ✅ **对话搜索** — 根据关键词搜索历史对话

### 评测系统
- ✅ **批量评测** — 在 VQA-v2、TextVQA 或自定义数据集上批量评测
- ✅ **多指标** — 精确匹配、包含匹配、综合准确率
- ✅ **错误分析** — 自动分类错误类型（OCR错误、内容不匹配等 7 类）
- ✅ **数据集自动检测** — 标准路径下的数据集自动识别，不可用时给出下载指引

### 案例分析
- ✅ **案例收集** — 从评测结果或手动添加成功/失败案例
- ✅ **分析报告** — 生成 Markdown / JSON 格式的案例分析报告
- ✅ **错误分类** — 记录每个失败案例的错误类型和人工分析

### 命令行工具
- ✅ **CLI 交互界面** — `python cli.py` 进入命令行对话模式
- ✅ **CLI 批量评测** — `python cli.py --eval --samples 20` 运行评测

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI + Uvicorn |
| VLM API | 阿里云通义千问 VL (Qwen-VL) / 智谱 AI GLM-4V |
| 前端框架 | Vue 3 + Element Plus |
| 构建工具 | Vite |
| Markdown | marked |
| CLI | Python + Rich |

## 快速开始

### 1. 环境初始化（仅需一次）

```bash
cd code

# macOS / Linux
bash scripts/setup.sh

# Windows
scripts\setup.bat
```

脚本会自动完成：检查 Python/Node.js → 创建虚拟环境 → 安装依赖 → 提示配置 .env。

### 2. 配置 API 密钥

编辑 `backend/.env`，至少填入一个 API 密钥：

```env
VLM_API_PROVIDER=qwen                          # qwen 或 zhipu
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx          # 通义千问（推荐）
# 或
ZHIPU_API_KEY=xxxxxxxxxxxxxxxx                 # 智谱 AI
```

- 通义千问: https://dashscope.console.aliyun.com/
- 智谱 AI: https://open.bigmodel.cn/

### 3. 启动服务

```bash
cd code

# macOS / Linux — 启动前后端 + 自动打开浏览器
bash scripts/start.sh

# 仅启动后端
bash scripts/start.sh backend

# Windows
scripts\start.bat
```

- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs
- 前端界面: http://localhost:3000

## 图像类型切换

聊天界面顶部有图像类型选择器，支持四种模式：

| 模式 | 说明 | 系统提示词效果 |
|------|------|--------------|
| 🌄 自然场景 | 通用自然图像理解 | 关注物体、人物、场景、颜色、动作等 |
| 📄 文档 | 文档/表格分析 | 识别文字内容、文档结构、表格数据 |
| 📊 幻灯片 | 课件/PPT 解读 | 理解逻辑结构、要点层次、图表解读 |
| 🛍️ 商品 | 商品识别与分析 | 关注外观特征、功能参数、使用建议 |

**切换后模型的实际行为会改变** — 例如"文档"模式会重点识别图片中的文字和表格，"商品"模式会关注产品特征和使用建议。

## 数据集评测指南

### 数据集目录结构

公开数据集请下载到 `data/datasets/` 目录下：

```
data/datasets/
├── README.md              # 详细下载说明
├── sample_custom.json     # 自定义数据集格式示例
│
├── vqa_v2/                # VQA-v2 数据集 (~6.5 GB)
│   ├── v2_OpenEnded_mscoco_val2014_questions.json
│   ├── v2_mscoco_val2014_annotations.json
│   └── val2014/           # COCO val2014 图片
│       └── COCO_val2014_000000000001.jpg ...
│
└── textvqa/               # TextVQA 数据集 (~2 GB)
    ├── TextVQA_0.5.1_val_questions.json
    ├── TextVQA_0.5.1_val_annotations.json
    └── val_images/        # TextVQA 图片
```

### 下载地址

| 数据集 | 下载 | 大小 |
|--------|------|------|
| VQA-v2 | https://visualqa.org/download.html | ~6.5 GB |
| TextVQA | https://textvqa.org/download/ | ~2 GB |

下载后按上述目录结构解压，系统会自动检测。

### 运行评测

**Web 界面**：点击侧边栏"📊 批量评测"，选择数据集类型即可。

**CLI**：
```bash
cd code
python cli.py --eval --dataset builtin --image-type natural_scene --samples 20
python cli.py --eval --dataset vqa_v2 --samples 50
```

**API**：
```bash
curl -X POST http://localhost:8000/api/v1/evaluate/batch \
  -H "Content-Type: application/json" \
  -d '{"dataset_type":"builtin","image_type":"natural_scene","max_samples":10}'
```

### 评测指标

- **包含匹配准确率** — 预测中包含标准答案（或反之），宽松匹配
- **精确匹配准确率** — 完全一致才算正确
- **综合准确率** — 包含匹配或精确匹配之一满足
- **错误类型分类** — 空响应 / OCR错误 / 内容不匹配 / 模型拒答 / 回答不完整 等

### 案例分析

评测结果会自动同步到案例分析器。点击侧边栏"📋 案例分析报告"查看。也可以手动将对话中的回答添加到案例库。

## API 接口

### 对话
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/chat` | 图文问答（JSON body，含 image_type） |
| POST | `/chat/upload` | 图文问答（FormData 上传图片） |
| GET | `/conversation/{id}` | 获取对话 |
| DELETE | `/conversation/{id}` | 删除对话 |
| POST | `/conversation/{id}/clear` | 清空对话 |
| GET | `/conversations` | 对话列表 |
| GET | `/conversation/{id}/export` | 导出对话（json/markdown） |
| POST | `/conversation/import` | 导入对话 |
| GET | `/conversations/search` | 搜索对话 |

### 评测
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/evaluate` | 单条评测 |
| POST | `/evaluate/batch` | 批量评测数据集 |
| GET | `/evaluate/report` | 快速评测报告 |
| GET | `/evaluate/datasets` | 数据集可用状态 |

### 案例
| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/cases` | 案例列表 / 添加案例 |
| GET | `/cases/report` | 案例报告（json/markdown） |
| GET | `/cases/{id}` | 案例详情 |
| PUT | `/cases/{id}/analysis` | 更新案例分析 |
| DELETE | `/cases` | 清空案例 |

### 其他
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/prompts` | 系统提示词模板 |

## 聊天请求示例

```json
{
  "message": "这张图片中有什么？",
  "image_base64": "base64编码的图片数据",
  "conversation_id": "可选",
  "history": [],
  "image_type": "document"
}
```

## 配置说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| VLM_API_PROVIDER | API 服务商 (qwen/zhipu) | qwen |
| DASHSCOPE_API_KEY | 通义千问 API 密钥 | - |
| ZHIPU_API_KEY | 智谱 AI API 密钥 | - |
| MODEL_NAME | 模型名称 | qwen-vl-plus |
| MAX_HISTORY_LENGTH | 最大历史轮数 | 10 |
| MAX_TOKENS | 最大生成 token 数 | 2048 |
| TEMPERATURE | 温度参数 | 0.7 |

## CLI 使用方法

```bash
cd code

# 交互式对话
python cli.py

# 命令行内发送图片
#   image:/path/to/photo.jpg 请描述这张图片

# 批量评测
python cli.py --eval --samples 20

# 指定 API 地址
python cli.py --api http://localhost:8000/api/v1

# 评测并保存报告
python cli.py --eval --output eval_report.json
```

## 注意事项

1. **API 费用**: 云端 API 调用会产生费用，请注意用量
2. **图片大小**: 建议不超过 5MB
3. **并发限制**: 批量评测时自动控制并发数为 2，避免 API 限流
4. **网络**: 需要稳定网络连接访问云端 API
5. **内置测试不含图片**: "管线测试"模式仅有文本问答对，不能评估 VLM 的看图能力

## 许可证

MIT License
