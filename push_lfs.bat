@echo off
chcp 65001 >nul
title iData 知识库 - 一键推送（Git LFS版）

:: ========== 在这填入你的 GitHub Token ==========
set GIT_TOKEN=在这里填入你的新 token（ghp_ 开头）
:: =======================================================

if "%GIT_TOKEN%"=="在这里填入你的新 token（ghp_ 开头）" (
    echo.
    echo [错误] 请先编辑此文件，填入你的 GitHub Token！
    echo 步骤：
    echo   1. 右键此文件 → 编辑
    echo   2. 把第 7 行的 token 替换成你的新 token
    echo   3. 保存后重新运行
    echo.
    pause
    exit /b 1
)

echo ==========================================
echo   iData 知识库 - Git LFS 推送脚本
echo ==========================================
echo.

:: 切换到仓库目录
cd /d "D:\Claw\文档处理\使用说明书"
if errorlevel 1 (
    echo [错误] 目录不存在，请检查路径
    pause & exit /b 1
)

echo [1/5] 检查 Git LFS...
git lfs version >nul 2>&1
if errorlevel 1 (
    echo [提示] Git LFS 未安装，正在安装...
    git lfs install --system
)

echo [2/5] 配置 LFS 追踪规则...
git lfs track "*.pdf" >nul 2>&1
git lfs track "*.docx" >nul 2>&1
git lfs track "*.doc" >nul 2>&1
git add .gitattributes 2>nul

echo [3/5] 暂存所有文件...
git add -A
git status --short

echo.
set /p MSG=请输入本次更新说明（回车用默认）: 
if "%MSG%"=="" set MSG=文档更新 %date:~0,4%-%date:~5,2%-%date:~8,2%

echo [4/5] 提交: %MSG%
git commit -m "%MSG%" 2>nul || echo （无新变更，跳过提交）

echo [5/5] 推送到 GitHub（LFS）...
git remote set-url origin https://RayZrz:%GIT_TOKEN%@github.com/RayZrz/idata-docs.git
git push -u origin main 2>&1

if errorlevel 1 (
    echo.
    echo [错误] 推送失败，请检查：
    echo   1. Token 是否正确（有 repo 权限）
    echo   2. 网络是否正常
    echo   3. 仓库是否存在且为 Public
    echo.
) else (
    echo.
    echo ==========================================
    echo   ✅ 推送成功！
    echo   下一步：配置 Cloudflare Pages
    echo   地址：https://dash.cloudflare.com
    echo ==========================================
)

echo.
pause
