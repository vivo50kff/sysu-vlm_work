@echo off
chcp 65001 >nul
REM ============================================================
REM VLM图文问答助手 - 服务启动脚本 (Windows)
REM 用法: cd code && scripts\start.bat            全部
REM       cd code && scripts\start.bat backend     仅后端
REM       cd code && scripts\start.bat frontend    仅前端
REM ============================================================

setlocal enabledelayedexpansion

set MODE=%1
if "%MODE%"=="" set MODE=all

set BACKEND_PORT=8000
set FRONTEND_PORT=3000

REM 路径
set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."
set "BACKEND_DIR=%PROJECT_DIR%\backend"
set "FRONTEND_DIR=%PROJECT_DIR%\frontend"

echo.
echo ╔══════════════════════════════════════════════════╗
echo ║        🤖 VLM图文问答助手 - 启动服务             ║
echo ╚══════════════════════════════════════════════════╝
echo.

REM ==================== 预检 ====================

cd /d "%BACKEND_DIR%"

if not exist ".env" (
    echo [ERR]  .env 文件不存在！请先运行 scripts\setup.bat 初始化环境
    goto :end
)

findstr /c:"your_dashscope_api_key_here" .env >nul 2>nul
set ENV_DS=%errorlevel%
findstr /c:"your_zhipu_api_key_here" .env >nul 2>nul
set ENV_ZP=%errorlevel%

if %ENV_DS% equ 0 if %ENV_ZP% equ 0 (
    echo [ERR]  .env 中的 API 密钥尚未配置！
    echo.
    echo   请编辑 backend\.env，至少填入一个 API 密钥：
    echo   - DASHSCOPE_API_KEY (通义千问^): https://dashscope.console.aliyun.com/
    echo   - ZHIPU_API_KEY (智谱AI^):       https://open.bigmodel.cn/
    echo.
    echo   编辑命令: notepad backend\.env
    goto :end
)
echo [OK]   .env 配置检查通过

if not exist "venv\Scripts\activate.bat" (
    echo [ERR]  虚拟环境不存在，请先运行 scripts\setup.bat
    goto :end
)

cd /d "%BACKEND_DIR%"
if not exist "logs" mkdir logs
if not exist "data\conversations" mkdir data\conversations
if not exist "data\cases" mkdir data\cases

echo.
echo   后端 API:  http://localhost:%BACKEND_PORT%
echo   API 文档:  http://localhost:%BACKEND_PORT%/docs
echo   前端界面:  http://localhost:%FRONTEND_PORT%
echo.

REM ==================== 释放端口 ====================
echo [INFO] 检查端口占用...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%BACKEND_PORT% " ^| findstr "LISTENING" 2^>nul') do (
    echo [WARN] 端口 %BACKEND_PORT% 被占用 (PID: %%a^)，正在释放...
    taskkill /PID %%a /F >nul 2>nul
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%FRONTEND_PORT% " ^| findstr "LISTENING" 2^>nul') do (
    echo [WARN] 端口 %FRONTEND_PORT% 被占用 (PID: %%a^)，正在释放...
    taskkill /PID %%a /F >nul 2>nul
)

cd /d "%PROJECT_DIR%"

REM ==================== 启动 ====================
if "%MODE%"=="all" goto :all
if "%MODE%"=="backend" goto :backend
if "%MODE%"=="frontend" goto :frontend
goto :all

:all
    echo [INFO] 启动后端 + 前端...
    echo.

    start "VLM-后端" cmd /c "cd /d %BACKEND_DIR% && venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload"
    timeout /t 3 /nobreak >nul

    start "VLM-前端" cmd /c "cd /d %FRONTEND_DIR% && npx vite --port %FRONTEND_PORT% --strictPort"
    timeout /t 3 /nobreak >nul

    start http://localhost:%FRONTEND_PORT%
    echo [OK]   浏览器已打开
    goto :done

:backend
    echo [INFO] 启动后端...
    call "%BACKEND_DIR%\venv\Scripts\activate.bat"
    cd /d "%BACKEND_DIR%"
    python -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload
    start http://localhost:%BACKEND_PORT%/docs
    goto :done

:frontend
    echo [INFO] 启动前端...
    cd /d "%FRONTEND_DIR%"
    npx vite --port %FRONTEND_PORT% --strictPort
    start http://localhost:%FRONTEND_PORT%
    goto :done

:done
echo.
echo ╔══════════════════════════════════════════════════╗
echo ║              ✅ 服务启动完成!                     ║
echo ╚══════════════════════════════════════════════════╝
echo.
echo   按 Ctrl+C 停止当前窗口的服务
echo   (独立窗口的服务直接关闭窗口即可^)
echo.

:end
echo.
pause
