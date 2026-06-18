@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   微信公众号发布工作台
echo ========================================
echo.

REM 检查环境变量
set "MISSING="
if not defined APIMART_API_KEY set "MISSING=%MISSING% APIMART_API_KEY"
if not defined WECHAT_APPID set "MISSING=%MISSING% WECHAT_APPID"
if not defined WECHAT_APPSECRET set "MISSING=%MISSING% WECHAT_APPSECRET"
if not defined EXA_API_KEY echo   [提示] 未设置 EXA_API_KEY，将无法使用搜索功能

if defined MISSING (
    echo [警告] 缺少环境变量:%MISSING%
    echo.
    echo 请先设置环境变量，例如：
    echo   setx APIMART_API_KEY "your-key"
    echo   setx WECHAT_APPID "wx..."
    echo   setx WECHAT_APPSECRET "your-secret"
    echo.
    echo 或者在 PowerShell 当前会话临时设置：
    echo   $env:APIMART_API_KEY="your-key"
    echo.
    set /p CONTINUE="按回车继续启动（部分功能将不可用），或 Ctrl+C 取消..."
)

echo 启动服务...
echo 浏览器打开: http://localhost:8765
echo 按 Ctrl+C 停止
echo.

python server.py

pause
