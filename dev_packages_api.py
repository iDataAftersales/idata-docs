#!/usr/bin/env python3
"""
iData 开发包 HTTP API
供 Dify 智能体调用的开发包查询接口

数据源优先级：
  1. 扫描本地 开发包/ 目录（最实时，需要文件系统访问权限）
  2. dev_packages_catalog.json（缓存，由 sync_dev_packages.py 生成）
  3. 从 GitHub Pages 获取 JSON（适合无本地文件场景）

运行: python dev_packages_api.py
默认端口: 8001
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
import os
import urllib.parse
import asyncio
from datetime import date

app = FastAPI(
    title="iData 开发包 API",
    description="供 Dify 智能体调用的开发包查询接口（支持动态目录扫描）",
    version="1.1"
)

# CORS — 允许 Dify 跨域调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 配置 ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEV_PKG_DIR = os.path.join(BASE_DIR, "开发包")
DATA_FILE = os.path.join(BASE_DIR, "dev_packages_catalog.json")
GITHUB_JSON_URL = (
    "https://idataaftersales.github.io/idata-docs/dev_packages_catalog.json"
)

# ==================== 分类推断 ====================
CATEGORY_KEYWORDS = {
    "UHF": ["uhf"],
    "iScanPro": ["iscanpro", "iscanplus", "iscan"],
    "TSPL指令集": ["tspl", "d400", "z400"],
    "RFID": ["rfid"],
    "NFC": ["nfc"],
}


def guess_category(filename):
    fname_lower = filename.lower()
    for cat, kws in CATEGORY_KEYWORDS.items():
        for kw in kws:
            if kw in fname_lower:
                return cat
    return "其他"


def guess_name(filename):
    import re
    name = os.path.splitext(filename)[0]
    name = re.sub(r'[Vv]\d+(\.\d+)*.*$', '', name)
    name = re.sub(r'【.*?】', '', name)
    name = re.sub(r'_\d{8}$', '', name)
    return name.strip('_- ')


def guess_version(filename):
    import re
    m = re.search(r'[Vv](\d+(\.\d+)*)', filename)
    if m:
        return 'V' + m.group(1)
    m = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    if m:
        return m.group(1)
    return ""


def guess_year(filename):
    import re
    m = re.search(r'(\d{4})', filename)
    return m.group(1) if m else str(date.today().year)


def format_size(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"


# ==================== 数据加载 ====================

def scan_local_directory():
    """
    动态扫描 开发包/ 目录，返回 packages 列表。
    不需要依赖 JSON 文件，有新文件立即识别。
    """
    if not os.path.isdir(DEV_PKG_DIR):
        return None  # 目录不存在，返回 None 让上层用其他数据源

    packages = []
    existing_filenames = set()
    next_id = 1

    # 也读一下 JSON 获取已有 ID（保留手动编辑的字段）
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for p in data.get('packages', []):
                existing_filenames.add(p['filename'])
                try:
                    num = int(p['id'].split('-')[-1])
                    next_id = max(next_id, num + 1)
                except Exception:
                    pass
        except Exception:
            pass

    # 扫描文件
    for entry in os.listdir(DEV_PKG_DIR):
        full_path = os.path.join(DEV_PKG_DIR, entry)
        if os.path.isdir(full_path):
            for root, dirs, files in os.walk(full_path):
                for f in files:
                    if not f.lower().endswith('.zip'):
                        continue
                    if f in existing_filenames:
                        continue
                    fpath = os.path.join(root, f)
                    rel_path = os.path.relpath(fpath, BASE_DIR).replace('\\', '/')
                    size = os.path.getsize(fpath)
                    pkg = _make_pkg(f, rel_path, size, next_id)
                    next_id += 1
                    existing_filenames.add(f)
                    packages.append(pkg)
            continue

        if not entry.lower().endswith('.zip'):
            continue
        if entry in existing_filenames:
            continue

        size = os.path.getsize(full_path)
        rel_path = f"开发包/{entry}"
        pkg = _make_pkg(entry, rel_path, size, next_id)
        next_id += 1
        packages.append(pkg)

    return packages


def _make_pkg(filename, rel_path, size, id_num):
    encoded_path = urllib.parse.quote(rel_path, safe='/')
    return {
        "id": f"pkg-{id_num:03d}",
        "category": guess_category(filename),
        "name": guess_name(filename),
        "year": guess_year(filename),
        "version": guess_version(filename),
        "format": "zip",
        "filename": filename,
        "path": rel_path,
        "size": format_size(size),
        "description": guess_name(filename),
        "download_url": f"https://idataaftersales.github.io/idata-docs/{encoded_path}",
        "tags": [guess_category(filename)]
    }


def load_data(scan_dir=True):
    """
    加载数据，优先级：
      1. 扫描本地目录（如果 scan_dir=True 且目录可访问）
      2. 读取本地 JSON 文件
      3. 返回空列表
    """
    packages = []

    # 优先扫描目录
    if scan_dir:
        scanned = scan_local_directory()
        if scanned is not None:
            # 扫描到了新文件，合并到 JSON 数据
            packages = scanned

    # 补充 JSON 中已有的、但目录扫描未覆盖的字段（如下载次数等扩展字段）
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            json_pkgs = {p['filename']: p for p in data.get('packages', [])}
            # 用 JSON 中的数据补充扫描结果的字段
            for p in packages:
                if p['filename'] in json_pkgs:
                    # 保留 JSON 中特有的字段（如手动添加的描述）
                    for k, v in json_pkgs[p['filename']].items():
                        if k not in p or not p[k]:
                            p[k] = v
            # 也加入扫描未发现的（可能已删除文件但 JSON 还有记录）
            scanned_fnames = {p['filename'] for p in packages}
            for fname, p in json_pkgs.items():
                if fname not in scanned_fnames:
                    packages.append(p)
        except Exception:
            pass

    if not packages:
        # 兜底：从 GitHub Pages 获取
        packages = _fetch_github_json()

    return {"version": "1.1", "lastUpdated": date.today().isoformat(), "packages": packages}


def _fetch_github_json():
    """从 GitHub Pages 获取 JSON（无本地文件时使用）"""
    try:
        import urllib.request
        with urllib.request.urlopen(GITHUB_JSON_URL, timeout=5) as r:
            data = json.loads(r.read())
            return data.get('packages', [])
    except Exception:
        return []


# ==================== 接口 ====================

@app.get("/")
def root():
    return {
        "service": "iData 开发包 API",
        "version": "1.1",
        "features": ["动态目录扫描", "CORS 跨域", "GitHub JSON 兜底"],
        "endpoints": [
            "GET  /packages               — 列出所有开发包",
            "GET  /packages?category=UHF — 按分类筛选",
            "GET  /packages/{id}         — 查询单个开发包",
            "GET  /packages/search?q=xxx — 关键词搜索",
            "GET  /categories             — 列出所有分类",
            "POST /refresh               — 强制刷新（重新扫描目录）",
        ]
    }


@app.get("/packages")
def list_packages(
    category: str = Query(None, description="按分类筛选，如 UHF、iScanPro、TSPL指令集"),
    format: str = Query(None, description="按格式筛选，如 zip"),
    scan: bool = Query(True, description="是否扫描本地目录（设为 false 仅读 JSON）")
):
    """列出所有开发包，支持按分类/格式筛选"""
    data = load_data(scan_dir=scan)
    packages = data.get("packages", [])

    if category:
        packages = [p for p in packages if p.get("category") == category]
    if format:
        packages = [p for p in packages if p.get("format") == format]

    return {
        "total": len(packages),
        "category_filter": category,
        "format_filter": format,
        "scanned": scan,
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
    data = load_data(scan_dir=True)
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
def get_package(pkg_id: str, scan: bool = Query(True)):
    """按 ID 查询单个开发包详情"""
    data = load_data(scan_dir=scan)
    packages = data.get("packages", [])
    for p in packages:
        if p.get("id") == pkg_id:
            return p
    raise HTTPException(status_code=404, detail=f"开发包不存在: {pkg_id}")


@app.get("/categories")
def list_categories():
    """列出所有开发包分类及数量"""
    data = load_data(scan_dir=True)
    packages = data.get("packages", [])
    cats = {}
    for p in packages:
        c = p.get("category", "未分类")
        cats[c] = cats.get(c, 0) + 1
    return {
        "total_categories": len(cats),
        "categories": [{"name": k, "count": v} for k, v in cats.items()]
    }


@app.post("/refresh")
def refresh():
    """
    强制刷新：重新扫描目录并更新 JSON。
    需要在有文件系统访问权限的环境中调用（本地或同机部署）。
    """
    packages = scan_local_directory()
    if packages is None:
        return {"status": "error", "detail": "本地目录不可访问，无法扫描"}

    data = {"version": "1.1", "lastUpdated": date.today().isoformat(),
             "packages": packages}
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {"status": "ok", "total": len(packages),
            "message": f"已刷新并更新 {DATA_FILE}"}


@app.get("/health")
def health():
    data = load_data(scan_dir=False)
    return {
        "status": "ok",
        "packages_count": len(data.get("packages", [])),
        "local_dir_accessible": os.path.isdir(DEV_PKG_DIR),
        "json_file_exists": os.path.exists(DATA_FILE),
    }


# ==================== 启动 ====================
if __name__ == "__main__":
    import uvicorn
    print("启动 iData 开发包 API v1.1 ...")
    print("  - 动态目录扫描: ", os.path.isdir(DEV_PKG_DIR))
    print("  - JSON 文件: ", os.path.exists(DATA_FILE))
    print("接口文档: http://localhost:8001/docs")
    print("调用示例: curl http://localhost:8001/packages")
    uvicorn.run(app, host="0.0.0.0", port=8001)
