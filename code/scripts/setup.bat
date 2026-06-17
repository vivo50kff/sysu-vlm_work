@echo off
chcp 65001 >nul
REM ============================================================
REM VLM图文问答助手 - 环境初始化脚本 (Windows)
REM 用法: cd code && scripts\setup.bat
REM ============================================================

setlocal enabledelayedexpansion

REM 路径 (scripts\ 的上级是 code\)
set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."
set "BACKEND_DIR=%PROJECT_DIR%\backend"
set "FRONTEND_DIR=%PROJECT_DIR%\frontend"

echo.
echo ╔══════════════════════════════════════════════════╗
echo ║    🤖 VLM图文问答助手 - 环境初始化 (Windows)     ║
echo ╚══════════════════════════════════════════════════╝
echo.

REM ==================== 1. 检查 Python ====================
echo [INFO] 检查 Python 环境...

set PYTHON=
for %%c in (python python3) do (
    where %%c >nul 2>nul
    if !errorlevel! equ 0 (
        for /f "tokens=2 delims= " %%v in ('%%c --version 2^>^&1') do (
            set ver=%%v
            for /f "tokens=1,2 delims=." %%a in ("!ver!") do (
                if %%a geq 3 if %%b geq 10 set PYTHON=%%c
            )
        )
    )
)

if "%PYTHON%"=="" (
    echo [ERR]  需要 Python 3.10+，当前未找到或版本过低
    echo         请安装: https://www.python.org/downloads/
    goto :end
)
echo [OK]   Python 已找到

REM ==================== 2. 检查 Node.js ====================
set NODE_OK=0
where node >nul 2>nul
if %errorlevel% equ 0 (
    for /f "tokens=1 delims=v." %%v in ('node --version 2^>^&1') do (
        if %%v geq 16 set NODE_OK=1
    )
)
if %NODE_OK% equ 1 (
    echo [OK]   Node.js 已找到
) else (
    echo [WARN] Node.js 未安装或版本过低 (需要 16+^)，前端将无法运行
    echo         安装: https://nodejs.org/
)

REM ==================== 3. 后端虚拟环境 ====================
echo.
echo [INFO] 配置后端 Python 虚拟环境...

cd /d "%BACKEND_DIR%"

if not exist "venv" (
    %PYTHON% -m venv venv
    echo [OK]   虚拟环境已创建: backend\venv\
) else (
    echo [OK]   虚拟环境已存在: backend\venv\
)

call venv\Scripts\activate.bat

echo [INFO] 安装 Python 依赖...
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo [OK]   Python 依赖安装完成

REM ==================== 4. 前端依赖 ====================
if exist "%FRONTEND_DIR%" (
    if %NODE_OK% equ 1 (
        echo [INFO] 安装前端依赖...
        cd /d "%FRONTEND_DIR%"
        call npm install --silent 2>nul
        cd /d "%BACKEND_DIR%"
        echo [OK]   前端依赖安装完成
    )
)

REM ==================== 5. .env 配置提示 ====================
echo.
echo ╔══════════════════════════════════════════════════╗
echo ║            ⚠️  配置 API 密钥                      ║
echo ╚══════════════════════════════════════════════════╝
echo.

if not exist ".env" (
    echo [WARN] .env 文件不存在！
    echo.
    echo   请参考 .env.example 模板创建 .env 文件：
    echo.
    echo     copy backend\.env.example backend\.env
    echo     notepad backend\.env       (填入你的 API 密钥^)
    echo.
) else (
    findstr /c:"your_dashscope_api_key_here" .env >nul 2>nul
    if %errorlevel% equ 0 (
        echo [WARN] .env 文件中的 API 密钥仍为占位值！
        echo.
        echo   请编辑 backend\.env，至少填入一个 API 密钥：
        echo.
        echo   - 通义千问: DASHSCOPE_API_KEY   获取: https://dashscope.console.aliyun.com/
        echo   - 智谱AI:   ZHIPU_API_KEY       获取: https://open.bigmodel.cn/
        echo.
    ) else (
        echo [OK]   .env 文件已配置
    )
)

REM ==================== 6. 创建必要目录 ====================
if not exist "logs" mkdir logs
if not exist "data\conversations" mkdir data\conversations
if not exist "data\cases" mkdir data\cases
echo [OK]   工作目录已就绪

REM ==================== 完成 ====================
cd /d "%PROJECT_DIR%"

echo.
echo ╔══════════════════════════════════════════════════╗
echo ║              ✅ 环境初始化完成!                   ║
echo ╚══════════════════════════════════════════════════╝
echo.
echo   下一步:
echo   ─────────────────────────────────────────────
echo   1. 配置 API 密钥:  编辑 backend\.env 文件
echo      (如果还没配置的话^)
echo.
echo   2. 启动全部服务:   scripts\start.bat
echo   ─────────────────────────────────────────────
echo.
echo   后端 API 文档:  http://localhost:8000/docs
echo   前端界面:      http://localhost:3000
echo.

:end
pause
