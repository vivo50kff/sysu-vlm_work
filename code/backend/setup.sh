#!/bin/bash

# VLM图文问答助手 - 后端环境设置脚本

echo "=== VLM图文问答助手 - 后端环境设置 ==="

# 进入后端目录
cd "$(dirname "$0")"

# 检查Python版本
echo "检查Python版本..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python版本: $python_version"

# 创建虚拟环境
echo "创建虚拟环境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "虚拟环境已创建: venv/"
else
    echo "虚拟环境已存在: venv/"
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "安装Python依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 检查.env文件
echo "检查环境变量配置..."
if [ ! -f ".env" ]; then
    echo "警告: .env文件不存在，正在从.env.example复制..."
    cp .env.example .env
    echo "请编辑 .env 文件，填入您的API密钥！"
else
    echo ".env文件已存在"
fi

echo ""
echo "=== 设置完成 ==="
echo ""
echo "使用方法:"
echo "1. 激活虚拟环境: source venv/bin/activate"
echo "2. 配置API密钥: 编辑 .env 文件"
echo "3. 启动服务: python -m app.main"
echo "4. 退出虚拟环境: deactivate"
echo ""