@echo off
chcp 65001 >nul
echo ====================================
echo PaperGraph - 一键启动所有服务
echo PaperGraph - Start All Services
echo ====================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未找到Python，请先安装Python 3.9+
    echo [ERROR] Cannot find Python, please install Python 3.9+ first
    pause
    exit /b 1
)

REM 步骤1: 运行setup（如果虚拟环境不存在）
if not exist "venv\" (
    echo ====================================
    echo 步骤 1/4: 设置环境
    echo Step 1/4: Setting up environment
    echo ====================================
    echo.
    call setup.bat
    if errorlevel 1 (
        echo [ERROR] 环境设置失败
        echo [ERROR] Environment setup failed
        pause
        exit /b 1
    )
    echo.
) else (
    echo [OK] 虚拟环境已存在
    echo [OK] Virtual environment already exists
    echo.
)

REM 激活虚拟环境
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] 无法激活虚拟环境
    echo [ERROR] Cannot activate virtual environment
    pause
    exit /b 1
)

REM 步骤2: 检查并启动Redis/Memurai服务
echo ====================================
echo 步骤 2/4: 检查Redis服务
echo Step 2/4: Checking Redis service
echo ====================================
echo.
sc query Memurai >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Memurai服务未运行，请手动启动
    echo [WARNING] Memurai service is not running, please start it manually
    echo 运行命令: net start Memurai
    echo Run command: net start Memurai
    echo.
) else (
    echo [OK] Redis/Memurai服务检查完成
    echo [OK] Redis/Memurai service check completed
    echo.
)

REM 步骤3: 启动后端服务器（在新窗口中）
echo ====================================
echo 步骤 3/4: 启动后端服务
echo Step 3/4: Starting backend services
echo ====================================
echo.

REM 启动FastAPI服务器
echo [INFO] 正在启动FastAPI服务器...
echo [INFO] Starting FastAPI server...
start "PaperGraph - FastAPI Server" cmd /k "cd /d %~dp0 && call venv\Scripts\activate.bat && echo ==================================== && echo FastAPI Server && echo ==================================== && echo Visit http://localhost:8000/docs for API documentation && echo Press Ctrl+C to stop server && echo. && python -m app.main"

REM 等待一下确保服务器启动
timeout /t 3 /nobreak >nul

REM 启动Celery Worker
echo [INFO] 正在启动Celery Worker...
echo [INFO] Starting Celery Worker...
start "PaperGraph - Celery Worker" cmd /k "cd /d %~dp0 && call venv\Scripts\activate.bat && set CELERY_BROKER_URL=redis://localhost:6379/1 && set CELERY_RESULT_BACKEND=redis://localhost:6379/2 && echo ==================================== && echo Celery Worker && echo ==================================== && echo Press Ctrl+C to stop worker && echo. && celery -A app.tasks.celery_app worker --loglevel=info --pool=solo"

REM 等待一下确保Worker启动
timeout /t 2 /nobreak >nul

REM 步骤4: 启动前端服务（在新窗口中）
echo ====================================
echo 步骤 4/4: 启动前端服务
echo Step 4/4: Starting frontend service
echo ====================================
echo.

set FRONTEND_DIR=knowledge_graph_system_v2\knowledge_graph_system_v2

if not exist "%FRONTEND_DIR%" (
    echo [ERROR] 前端目录不存在: %FRONTEND_DIR%
    echo [ERROR] Frontend directory not found: %FRONTEND_DIR%
    pause
    exit /b 1
)

REM 检查node_modules是否存在，如果不存在则先安装依赖
if not exist "%FRONTEND_DIR%\node_modules" (
    echo [INFO] 检测到前端依赖未安装，正在安装...
    echo [INFO] Frontend dependencies not found, installing...
    cd /d "%FRONTEND_DIR%"
    call npm install
    if errorlevel 1 (
        echo [ERROR] 前端依赖安装失败
        echo [ERROR] Frontend dependencies installation failed
        pause
        exit /b 1
    )
    cd /d %~dp0
    echo [OK] 前端依赖安装完成
    echo [OK] Frontend dependencies installed
    echo.
)

REM 启动前端服务
echo [INFO] 正在启动前端服务...
echo [INFO] Starting frontend service...
start "PaperGraph - Frontend Server" cmd /k "cd /d %~dp0\%FRONTEND_DIR% && echo ==================================== && echo Frontend Server && echo ==================================== && echo Visit http://localhost:3000 in your browser && echo Press Ctrl+C to stop server && echo. && npm run serve"

echo.
echo ====================================
echo 所有服务已启动！
echo All services started!
echo ====================================
echo.
echo 已打开以下窗口：
echo The following windows have been opened:
echo.
echo 1. FastAPI Server - http://localhost:8000
echo    API文档: http://localhost:8000/docs
echo    API Docs: http://localhost:8000/docs
echo.
echo 2. Celery Worker - 后台任务处理
echo    Background task processing
echo.
echo 3. Frontend Server - http://localhost:3000
echo    前端界面: http://localhost:3000
echo    Frontend UI: http://localhost:3000
echo.
echo ====================================
echo 提示: 关闭对应的窗口即可停止对应的服务
echo Tip: Close the corresponding window to stop the service
echo ====================================
echo.
echo 按任意键关闭此窗口...
echo Press any key to close this window...
pause >nul

