@echo off
REM VLM图文问答助手 - 后端环境设置脚本 (Windows)

echo === VLM图文问答助手 - 后端环境设置 ===

REM 进入后端目录
cd /d "%~dp0"

REM 检查Python版本
echo 检查Python版本...
python --version
echo.

REM 创建虚拟环境
echo 创建虚拟环境...
if not exist "venv" (
    python -m venv venv
    echo 虚拟环境已创建: venv\
) else (
    echo 虚拟环境已存在: venv\
)
echo.

REM 激活虚拟环境
echo 激活虚拟环境...
call venv\Scripts\activate.bat
echo.

REM 安装依赖
echo 安装Python依赖...
pip install --upgrade pip
pip install -r requirements.txt
echo.

REM 检查.env文件
echo 检查环境变量配置...
if not exist ".env" (
    echo 警告: .env文件不存在，正在从.env.example复制...
    copy .env.example .env
    echo 请编辑 .env 文件，填入您的API密钥！
) else (
    echo .env文件已存在
)
echo.

echo === 设置完成 ===
echo.
echo 使用方法:
echo 1. 激活虚拟环境: venv\Scripts\activate.bat
echo 2. 配置API密钥: 编辑 .env 文件
echo 3. 启动服务: python -m app.main
echo 4. 退出虚拟环境: deactivate
echo.

pause