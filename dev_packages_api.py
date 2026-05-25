#!/usr/bin/env python3
"""
iData 开发包 HTTP API
供 Dify 智能体调用的开发包查询接口
运行: python dev_packages_api.py
默认端口: 8000
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
import os
import urllib.parse

app = FastAPI(
    title="iData 开发包 API",
    description="供 Dify 智能体调用的开发包查询接口",
    version="1.0"
)

# CORS — 允许 Dify 跨域调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 数据加载 ====================
DATA_FILE = os.path.join(os.path.dirname(__file__), "dev_packages_catalog.json")

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"packages": [], "version": "1.0"}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_base_url():
    return "https://idataaftersales.github.io/idata-docs/"

# ==================== 接口 ====================

@app.get("/")
def root():
    return {
        "service": "iData 开发包 API",
        "version": "1.0",
        "endpoints": [
            "GET  /packages          — 列出所有开发包",
            "GET  /packages?category=UHF — 按分类筛选",
            "GET  /packages/{id}    — 查询单个开发包",
            "GET  /packages/search?q=xxx — 关键词搜索",
            "GET  /categories        — 列出所有分类",
        ]
    }

@app.get("/packages")
def list_packages(
    category: str = Query(None, description="按分类筛选，如 UHF、iScanPro、TSPL指令集"),
    format: str = Query(None, description="按格式筛选，如 zip")
):
    """列出所有开发包，支持按分类/格式筛选"""
    data = load_data()
    packages = data.get("packages", [])
    
    if category:
        packages = [p for p in packages if p.get("category") == category]
    if format:
        packages = [p for p in packages if p.get("format") == format]
    
    return {
        "total": len(packages),
        "category_filter": category,
        "format_filter": format,
        "packages": packages
    }

@app.get("/packages/search")
def search_packages(
    q: str = Query(..., description="搜索关键词，匹配 name/description/tags")
):
    """按关键词搜索开发包"""
    if not q or len(q.strip()) == 0:
        raise HTTPException(status_code=400, detail="q 参数不能为空")
    q = q.lower().strip()
    data = load_data()
    packages = data.get("packages", [])
    
    results = []
    for p in packages:
        search_text = " ".join([
            p.get("name", ""),
            p.get("description", ""),
            " ".join(p.get("tags", [])),
            p.get("category", "")
        ]).lower()
        if q in search_text:
            results.append(p)
    
    return {
        "query": q,
        "total": len(results),
        "packages": results
    }

@app.get("/packages/{pkg_id}")
def get_package(pkg_id: str):
    """按 ID 查询单个开发包详情"""
    data = load_data()
    packages = data.get("packages", [])
    for p in packages:
        if p.get("id") == pkg_id:
            # 补充下载链接
            if "download_url" not in p and p.get("filename"):
                encoded_name = urllib.parse.quote(p["filename"])
                p["download_url"] = get_base_url() + "开发包/" + encoded_name
            return p
    raise HTTPException(status_code=404, detail=f"开发包不存在: {pkg_id}")

@app.get("/categories")
def list_categories():
    """列出所有开发包分类及数量"""
    data = load_data()
    packages = data.get("packages", [])
    cats = {}
    for p in packages:
        c = p.get("category", "未分类")
        cats[c] = cats.get(c, 0) + 1
    return {
        "total_categories": len(cats),
        "categories": [{"name": k, "count": v} for k, v in cats.items()]
    }

@app.get("/health")
def health():
    data = load_data()
    return {"status": "ok", "packages_count": len(data.get("packages", []))}

# ==================== 启动 ====================
if __name__ == "__main__":
    import uvicorn
    print("启动 iData 开发包 API...")
    print("接口文档: http://localhost:8001/docs")
    print("调用示例: curl http://localhost:8001/packages")
    uvicorn.run(app, host="0.0.0.0", port=8001)
