@echo off
echo ====================================
echo PaperGraph Celery Worker Starter
echo ====================================
echo.

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo [OK] Virtual environment activated
) else (
    echo [ERROR] Cannot find virtual environment, please run setup.bat first
    pause
    exit /b 1
)

echo.
echo Activating Celery Worker...
echo.
echo Press Ctrl+C to stop Worker
echo.

rem 确保 Celery 使用无密码的 Redis 连接（与本地 Redis 无密码配置一致）
set CELERY_BROKER_URL=redis://localhost:6379/1
set CELERY_RESULT_BACKEND=redis://localhost:6379/2

celery -A app.tasks.celery_app worker --loglevel=info --pool=solo

pause