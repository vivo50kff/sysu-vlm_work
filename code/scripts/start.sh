#!/bin/bash
# ============================================================
# VLM图文问答助手 - 服务启动脚本 (macOS / Linux)
# 用法: cd code && bash scripts/start.sh            全部
#       cd code && bash scripts/start.sh backend     仅后端
#       cd code && bash scripts/start.sh frontend    仅前端
#       cd code && bash scripts/start.sh --no-browser 不打开浏览器
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
err()   { echo -e "${RED}[ERR]${NC}   $1"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

MODE="all"
OPEN_BROWSER=true
PIDS=()
BACKEND_PORT=8000
FRONTEND_PORT=3000
FRONTEND_ACTUAL_PORT=$FRONTEND_PORT
VITE_LOG=$(mktemp)
trap 'rm -f "$VITE_LOG"' EXIT

# 解析参数
for arg in "$@"; do
    case "$arg" in
        backend|frontend|all) MODE="$arg" ;;
        --no-browser) OPEN_BROWSER=false ;;
    esac
done

# ==================== 端口管理 ====================
kill_port() {
    local port=$1
    local pids
    pids=$(lsof -ti ":$port" 2>/dev/null)
    if [ -n "$pids" ]; then
        warn "端口 $port 被占用，正在释放..."
        echo "$pids" | while read -r pid; do
            kill "$pid" 2>/dev/null && info "  已终止进程 $pid (端口 $port)"
        done
        sleep 1
    fi
}

# ==================== 清理函数 ====================
cleanup() {
    echo ""
    warn "正在停止服务..."
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null
    done
    # 确保端口释放
    kill_port $BACKEND_PORT > /dev/null 2>&1
    kill_port $FRONTEND_ACTUAL_PORT > /dev/null 2>&1
    echo -e "${GREEN}服务已停止${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM

# ==================== 打开浏览器 ====================
open_browser() {
    local url="$1"
    if $OPEN_BROWSER; then
        sleep 2
        if command -v open &>/dev/null; then
            open "$url" 2>/dev/null && ok "浏览器已打开 → $url"
        fi
    fi
}

# ==================== 预检 ====================
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║        🤖 VLM图文问答助手 - 启动服务             ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# 检查 .env
cd "$BACKEND_DIR"
if [ ! -f ".env" ]; then
    err ".env 文件不存在！请先运行 bash scripts/setup.sh 初始化环境"
    exit 1
fi

if grep -q "your_dashscope_api_key_here" .env && grep -q "your_zhipu_api_key_here" .env; then
    err ".env 中的 API 密钥尚未配置！"
    echo ""
    echo "  请编辑 backend/.env，至少填入一个 API 密钥："
    echo "  - DASHSCOPE_API_KEY (通义千问): https://dashscope.console.aliyun.com/"
    echo "  - ZHIPU_API_KEY (智谱AI):       https://open.bigmodel.cn/"
    exit 1
fi
ok ".env 配置检查通过"

# ==================== 后端 ====================
start_backend() {
    echo ""
    info "启动后端服务 (端口 $BACKEND_PORT)..."

    if [ ! -f "$BACKEND_DIR/venv/bin/activate" ]; then
        err "虚拟环境不存在，请先运行 bash scripts/setup.sh"
        return 1
    fi

    # 释放可能占用的端口
    kill_port $BACKEND_PORT

    cd "$BACKEND_DIR"
    source venv/bin/activate
    mkdir -p logs data/conversations data/cases

    python -m uvicorn app.main:app \
        --host 0.0.0.0 \
        --port $BACKEND_PORT \
        --reload \
        > /dev/null 2>&1 &
    B_PID=$!
    PIDS+=("$B_PID")

    sleep 3

    if kill -0 "$B_PID" 2>/dev/null; then
        ok "后端已启动 → http://localhost:$BACKEND_PORT"
        ok "API 文档     → http://localhost:$BACKEND_PORT/docs"
    else
        err "后端启动失败，请检查 backend/logs/ 中的日志"
        return 1
    fi
}

# ==================== 前端 ====================
start_frontend() {
    echo ""
    info "启动前端服务 (端口 $FRONTEND_PORT)..."

    if [ ! -d "$FRONTEND_DIR" ]; then
        err "前端目录不存在: $FRONTEND_DIR"
        return 1
    fi

    if ! command -v node &>/dev/null; then
        err "Node.js 未安装"
        return 1
    fi

    # 释放可能占用的端口
    kill_port $FRONTEND_PORT

    cd "$FRONTEND_DIR"

    # 将 Vite 输出重定向到临时日志，以便解析实际端口
    npx vite --port $FRONTEND_PORT > /dev/null 2> "$VITE_LOG" &
    F_PID=$!
    PIDS+=("$F_PID")

    sleep 3

    if ! kill -0 "$F_PID" 2>/dev/null; then
        err "前端启动失败，查看日志: $VITE_LOG"
        return 1
    fi

    # 解析 Vite 实际使用的端口
    FRONTEND_ACTUAL_PORT=$(grep -oE 'Local:\s+http://localhost:[0-9]+' "$VITE_LOG" 2>/dev/null \
        | grep -oE '[0-9]+$' | head -1)
    if [ -z "$FRONTEND_ACTUAL_PORT" ]; then
        FRONTEND_ACTUAL_PORT=$FRONTEND_PORT
    fi

    if [ "$FRONTEND_ACTUAL_PORT" != "$FRONTEND_PORT" ]; then
        warn "端口 $FRONTEND_PORT 已被占用，Vite 自动切换到 $FRONTEND_ACTUAL_PORT"
    fi
    ok "前端已启动 → http://localhost:$FRONTEND_ACTUAL_PORT"
}

# ==================== 执行 ====================
FRONTEND_URL="http://localhost:$FRONTEND_PORT"

case "$MODE" in
    backend)
        start_backend && BROWSER_URL="http://localhost:$BACKEND_PORT/docs" || true
        ;;
    frontend)
        start_frontend && BROWSER_URL="http://localhost:$FRONTEND_ACTUAL_PORT" || true
        FRONTEND_URL="http://localhost:$FRONTEND_ACTUAL_PORT"
        ;;
    all|*)
        start_backend
        start_frontend
        BROWSER_URL="http://localhost:$FRONTEND_ACTUAL_PORT"
        FRONTEND_URL="http://localhost:$FRONTEND_ACTUAL_PORT"
        ;;
esac

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✅ 服务启动完成!                     ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo "  后端 API:  http://localhost:$BACKEND_PORT"
echo "  API 文档:  http://localhost:$BACKEND_PORT/docs"
echo "  前端界面:  $FRONTEND_URL"
echo ""
echo "  按 Ctrl+C 停止所有服务"
echo ""

if [ -n "$BROWSER_URL" ]; then
    open_browser "$BROWSER_URL"
fi

cd "$PROJECT_DIR"
wait
