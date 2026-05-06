# VLM图文问答助手

基于视觉语言模型（Vision-Language Model）的智能图文问答系统，支持图片理解与多轮对话。

## 项目结构

```
code/
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── api/            # API路由
│   │   │   ├── routes.py   # 路由定义
│   │   │   └── __init__.py
│   │   ├── services/       # 服务模块
│   │   │   ├── vlm_service.py          # VLM API服务
│   │   │   ├── conversation_manager.py # 对话管理
│   │   │   └── __init__.py
│   │   ├── models.py       # 数据模型
│   │   ├── config.py       # 配置管理
│   │   ├── main.py         # 主应用
│   │   └── __init__.py
│   ├── requirements.txt    # Python依赖
│   └── .env.example        # 环境变量示例
│
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── App.vue         # 主组件
│   │   ├── main.js         # 入口文件
│   │   ├── api.js          # API服务
│   │   └── style.css       # 样式文件
│   ├── index.html          # HTML模板
│   ├── package.json        # Node依赖
│   └── vite.config.js      # Vite配置
│
└── README.md               # 项目说明
```

## 功能特性

- ✅ 支持上传图片进行图文问答
- ✅ 支持多轮对话，保持上下文连贯
- ✅ 支持自然场景图像和文档/幻灯片图像
- ✅ 中文问答优化
- ✅ Markdown格式回复渲染
- ✅ 图片预览功能
- ✅ 对话历史管理

## 技术栈

### 后端
- **框架**: FastAPI
- **API服务**: 
  - 阿里云通义千问 VL (Qwen-VL)
  - 智谱AI GLM-4V
- **异步HTTP**: httpx, aiohttp

### 前端
- **框架**: Vue 3
- **UI组件**: Element Plus
- **构建工具**: Vite
- **Markdown渲染**: marked

## 快速开始

### 1. 配置API密钥

首先需要获取云端VLM API的密钥：

#### 通义千问 VL (推荐)
1. 访问 [阿里云DashScope](https://dashscope.console.aliyun.com/)
2. 注册并获取API Key
3. 选择模型: `qwen-vl-plus` 或 `qwen-vl-max`

#### 智谱AI GLM-4V
1. 访问 [智谱AI开放平台](https://open.bigmodel.cn/)
2. 注册并获取API Key
3. 选择模型: `glm-4v`

### 2. 后端启动

#### 方式一：使用设置脚本（推荐）

**macOS/Linux:**
```bash
# 进入后端目录
cd code/backend

# 运行设置脚本（自动创建虚拟环境并安装依赖）
chmod +x setup.sh
./setup.sh

# 激活虚拟环境
source venv/bin/activate

# 配置API密钥（编辑 .env 文件）
# DASHSCOPE_API_KEY=your_api_key_here
# 或
# ZHIPU_API_KEY=your_api_key_here

# 启动服务
python -m app.main
```

**Windows:**
```bash
# 进入后端目录
cd code/backend

# 运行设置脚本（自动创建虚拟环境并安装依赖）
setup.bat

# 激活虚拟环境（脚本会自动激活，或手动执行）
venv\Scripts\activate.bat

# 配置API密钥（编辑 .env 文件）
# DASHSCOPE_API_KEY=your_api_key_here
# 或
# ZHIPU_API_KEY=your_api_key_here

# 启动服务
python -m app.main
```

#### 方式二：手动设置

```bash
# 进入后端目录
cd code/backend

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate.bat

# 安装依赖
pip install -r requirements.txt

# 复制环境变量配置
cp .env.example .env

# 编辑 .env 文件，填入API密钥
# DASHSCOPE_API_KEY=your_api_key_here
# 或
# ZHIPU_API_KEY=your_api_key_here

# 启动服务
python -m app.main
# 或
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端服务将在 `http://localhost:8000` 启动，API文档可通过 `http://localhost:8000/docs` 访问。

### 3. 前端启动

```bash
# 进入前端目录
cd code/frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端应用将在 `http://localhost:3000` 启动。

### 4. 使用系统

1. 打开浏览器访问 `http://localhost:3000`
2. 点击图片按钮上传图片
3. 输入问题并发送
4. 查看AI回复

## API接口说明

### 聊天接口

**POST** `/api/v1/chat`

请求体:
```json
{
  "message": "这张图片中有什么？",
  "image_base64": "base64编码的图片数据",
  "conversation_id": "可选的对话ID",
  "history": "可选的对话历史"
}
```

响应:
```json
{
  "response": "这张图片展示了...",
  "conversation_id": "对话ID",
  "timestamp": "2024-01-01T12:00:00"
}
```

### 文件上传接口

**POST** `/api/v1/chat/upload`

表单数据:
- `message`: 用户消息
- `image`: 图片文件
- `conversation_id`: 可选的对话ID

### 其他接口

- `GET /api/v1/health` - 健康检查
- `GET /api/v1/conversation/{id}` - 获取对话历史
- `DELETE /api/v1/conversation/{id}` - 删除对话
- `POST /api/v1/conversation/{id}/clear` - 清空对话
- `GET /api/v1/conversations` - 列出所有对话

## 配置说明

### 环境变量 (.env)

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| VLM_API_PROVIDER | API服务商 (qwen/zhipu) | qwen |
| DASHSCOPE_API_KEY | 通义千问API密钥 | - |
| ZHIPU_API_KEY | 智谱AI API密钥 | - |
| MODEL_NAME | 模型名称 | qwen-vl-plus |
| MAX_HISTORY_LENGTH | 最大历史长度 | 10 |
| MAX_TOKENS | 最大生成token数 | 2048 |
| TEMPERATURE | 温度参数 | 0.7 |
| HOST | 服务主机 | 0.0.0.0 |
| PORT | 服务端口 | 8000 |
| DEBUG | 调试模式 | true |

## 评测说明

系统支持以下评测方式：

### 公开数据集评测
- VQA-v2: 自然图像问答
- TextVQA: 场景文本理解
- DocVQA: 文档问答

### 自建数据集评测
可使用 `/api/v1/evaluate` 接口进行评测：

```json
{
  "image_base64": "图片base64",
  "question": "问题",
  "ground_truth": "标准答案",
  "image_type": "natural_scene"
}
```

## 注意事项

1. **API费用**: 云端API调用会产生费用，请注意用量
2. **图片大小**: 建议图片大小不超过5MB
3. **并发限制**: 注意API的并发调用限制
4. **网络连接**: 需要稳定的网络连接访问云端API

## 开发计划

- [ ] 添加更多VLM API支持
- [ ] 实现本地模型推理选项
- [ ] 添加评测脚本
- [ ] 优化对话历史存储
- [ ] 添加用户认证

## 许可证

MIT License