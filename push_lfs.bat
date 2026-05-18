@echo off
chcp 65001 >nul
title iData 知识库 - 推送（LFS）

:: ========= 填入你的新 GitHub Token =========
set GIT_TOKEN=在这里填入新 token（ghp_ 开头）
:: ==================================================

if "%GIT_TOKEN%"=="在这里填入新 token（ghp_ 开头）" (
    echo.
    echo [错误] 请先填入 token！
    echo 右键编辑此文件，把第 7 行替换成你的新 token
    pause & exit /b 1
)

cd /d "D:\Claw\文档处理\使用说明书"

echo ==========================================
echo   iData 知识库 - 推送 LFS 大文件
echo ==========================================
echo.

echo [1/2] 提交变更...
git add -A
git commit -m "更新文档 %date:~0,4%-%date:~5,2%-%date:~8,2%" 2>nul || echo （无新变更跳过）

echo [2/2] 推送到 GitHub（LFS 大文件）...
git remote set-url origin https://RayZrz:%GIT_TOKEN%@github.com/RayZrz/idata-docs.git
git push -u origin main 2>&1

if errorlevel 1 (
    echo.
    echo [失败] 请检查 token 权限是否包含 repo
    echo 或访问 https://github.com/settings/tokens 重新生成
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
