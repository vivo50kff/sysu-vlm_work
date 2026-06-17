#!/bin/bash
# ============================================================
# VLM图文问答助手 - 环境初始化脚本 (macOS / Linux)
# 用法: cd code && bash scripts/setup.sh
# ============================================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
err()   { echo -e "${RED}[ERR]${NC}   $1"; }

# 项目根目录 (scripts/ 的上级)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     🤖 VLM图文问答助手 - 环境初始化 (macOS)      ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# ==================== 1. 检查 Python ====================
info "检查 Python 环境..."
PYTHON=""
for cmd in python3 python; do
    if command -v $cmd &>/dev/null; then
        ver=$($cmd --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
        major=$(echo "$ver" | cut -d. -f1)
        minor=$(echo "$ver" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            PYTHON=$cmd
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    err "需要 Python 3.10+，当前未找到或版本过低"
    echo "   请安装: https://www.python.org/downloads/"
    exit 1
fi
ok "Python $($PYTHON --version 2>&1)"

# ==================== 2. 检查 Node.js ====================
NODE_OK=false
if command -v node &>/dev/null; then
    node_ver=$(node --version | grep -oE '[0-9]+' | head -1)
    if [ "$node_ver" -ge 16 ]; then
        NODE_OK=true
    fi
fi
if $NODE_OK; then
    ok "Node.js $(node --version)"
else
    warn "Node.js 未安装或版本过低 (需要 16+)，前端将无法运行"
    echo "   安装: brew install node  或  https://nodejs.org/"
fi

# ==================== 3. 后端虚拟环境 ====================
info "配置后端 Python 虚拟环境..."
cd "$BACKEND_DIR"

if [ ! -d "venv" ]; then
    $PYTHON -m venv venv
    ok "虚拟环境已创建: backend/venv/"
else
    ok "虚拟环境已存在: backend/venv/"
fi

source venv/bin/activate

info "安装 Python 依赖..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
ok "Python 依赖安装完成"

# ==================== 4. 前端依赖 ====================
if [ -d "$FRONTEND_DIR" ] && $NODE_OK; then
    info "安装前端依赖..."
    cd "$FRONTEND_DIR"
    npm install --silent 2>/dev/null
    ok "前端依赖安装完成"
fi

# ==================== 5. .env 配置提示 ====================
cd "$BACKEND_DIR"

echo ""
echo -e "${YELLOW}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║            ⚠️  配置 API 密钥                      ║${NC}"
echo -e "${YELLOW}╚══════════════════════════════════════════════════╝${NC}"
echo ""

if [ ! -f ".env" ]; then
    warn ".env 文件不存在！"
    echo ""
    echo "  请参考 .env.example 模板创建 .env 文件："
    echo ""
    echo -e "    ${GREEN}cp backend/.env.example backend/.env${NC}"
    echo "   然后编辑 backend/.env 填入你的 API 密钥"
    echo ""
else
    if grep -q "your_dashscope_api_key_here" .env 2>/dev/null && grep -q "your_zhipu_api_key_here" .env 2>/dev/null; then
        warn ".env 文件中的 API 密钥仍为占位值！"
        echo ""
        echo "  请编辑 backend/.env，至少填入一个 API 密钥："
        echo ""
        echo "  - 通义千问: DASHSCOPE_API_KEY   获取: https://dashscope.console.aliyun.com/"
        echo "  - 智谱AI:   ZHIPU_API_KEY       获取: https://open.bigmodel.cn/"
        echo ""
    else
        ok ".env 文件已配置"
    fi
fi

# ==================== 6. 创建必要目录 ====================
mkdir -p logs data/conversations data/cases
ok "工作目录已就绪"

# ==================== 完成 ====================
cd "$PROJECT_DIR"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✅ 环境初始化完成!                   ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo "  下一步:"
echo "  ─────────────────────────────────────────────"
echo "  1. 配置 API 密钥:  编辑 backend/.env 文件"
echo "     (如果还没配置的话)"
echo ""
echo "  2. 启动全部服务:   bash scripts/start.sh"
echo "  ─────────────────────────────────────────────"
echo ""
echo "  后端 API 文档:  http://localhost:8000/docs"
echo "  前端界面:      http://localhost:3000"
echo ""
