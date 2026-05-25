#!/usr/bin/env python3
"""后台启动 FastAPI 开发包 API 服务"""
import subprocess
import sys
import time
import urllib.request
import json

# 启动服务
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "dev_packages_api:app", 
     "--host", "0.0.0.0", "--port", "8001"],
    cwd="D:/Claw/文档处理/使用说明书",
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

print(f"API 服务已启动 (PID: {proc.pid})")
print("等待服务就绪...")
time.sleep(3)

# 测试接口
try:
    url = "http://localhost:8001/packages"
    with urllib.request.urlopen(url, timeout=5) as r:
        data = json.loads(r.read())
        print(f"✅ /packages 接口正常，共 {data['total']} 个开发包")
        for p in data['packages']:
            print(f"  - {p['name']} ({p['category']})")
except Exception as e:
    print(f"❌ 接口测试失败: {e}")
    print("查看服务日志:")
    if proc.stdout:
        out = proc.stdout.read()
        print(out[:2000])

print(f"\n接口文档: http://localhost:8001/docs")
print(f"服务进程中，按 Ctrl+C 停止")
proc.wait()
