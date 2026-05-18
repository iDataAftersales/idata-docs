@echo off
chcp 65001 >nul
title iData 知识库 - 同步到 GitHub

echo ==========================================
echo   iData 产品文档知识库 - 一键同步脚本
echo ==========================================
echo.

:: 切换到仓库目录（修改为你的实际路径）
cd /d "D:\Claw\文档处理\使用说明书"

:: 检查 Git 是否初始化
if not exist ".git" (
    echo [初始化] 首次运行，正在初始化 Git 仓库...
    git init
    git branch -M main
    echo.
    echo [提示] 请先在 GitHub 创建仓库，然后运行：
    echo   git remote add origin https://github.com/你的用户名/idata-docs.git
    echo   然后重新运行此脚本
    pause
    exit /b 1
)

:: 检查是否有 remote
git remote -v >nul 2>&1
if errorlevel 1 (
    echo [错误] 尚未配置 GitHub 远程仓库
    echo 请运行: git remote add origin https://github.com/你的用户名/idata-docs.git
    pause
    exit /b 1
)

echo [步骤 1/4] 检查文件变更...
git status --short
echo.

:: 检查是否有变更
git diff --quiet && git diff --cached --quiet
if errorlevel 1 goto :has_changes

:: 检查未跟踪文件
for /f "tokens=*" %%i in ('git ls-files --others --exclude-standard') do (
    goto :has_changes
)

echo [提示] 没有检测到文件变更，无需同步。
echo.
pause
exit /b 0

:has_changes
echo [步骤 2/4] 暂存所有变更...
git add -A
echo.

:: 自动生成提交信息（含日期时间）
set DATETIME=%date:~0,4%-%date:~5,2%-%date:~8,2% %time:~0,2%:%time:~3,2%
set /p COMMIT_MSG=请输入本次更新说明（回车使用默认）: 
if "%COMMIT_MSG%"=="" set COMMIT_MSG=文档更新 %DATETIME%

echo [步骤 3/4] 提交变更: %COMMIT_MSG%
git commit -m "%COMMIT_MSG%"
echo.

echo [步骤 4/4] 推送到 GitHub...
git push origin main
if errorlevel 1 (
    echo.
    echo [错误] 推送失败，可能原因：
    echo   1. 网络问题，请检查网络连接
    echo   2. 需要登录，请先运行 git config 配置账号
    echo   3. 首次推送请运行: git push -u origin main
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   ✅ 同步成功！
echo   Cloudflare Pages 将在 1-2 分钟内自动部署
echo ==========================================
echo.
pause
