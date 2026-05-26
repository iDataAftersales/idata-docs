#!/usr/bin/env python3
"""
iData 开发包目录同步脚本
扫描 开发包/ 目录，自动更新 dev_packages_catalog.json，并可选 git push

用法:
    python sync_dev_packages.py              # 扫描并同步（不 push）
    python sync_dev_packages.py --push     # 同步并 git push
    python sync_dev_packages.py --dry-run  # 仅预览，不写入
"""

import json
import os
import re
import argparse
import subprocess
import sys
import urllib.parse
from datetime import date

# ==================== 配置 ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEV_PKG_DIR = os.path.join(BASE_DIR, "开发包")
JSON_FILE = os.path.join(BASE_DIR, "dev_packages_catalog.json")

# 已知分类映射（根据文件名关键词判断）
CATEGORY_KEYWORDS = {
    "UHF": ["uhf"],
    "iScanPro": ["iscanpro", "iscanplus", "iscan"],
    "TSPL指令集": ["tspl", "d400", "z400"],
    "RFID": ["rfid"],
    "NFC": ["nfc"],
}


def guess_category(filename):
    fname_lower = filename.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in fname_lower:
                return cat
    return "其他"


def guess_name(filename):
    name = os.path.splitext(filename)[0]
    name = re.sub(r'[Vv]\d+(\.\d+)*.*$', '', name)
    name = re.sub(r'【.*?】', '', name)
    name = re.sub(r'_\d{8}$', '', name)
    return name.strip('_- ')


def guess_version(filename):
    m = re.search(r'[Vv](\d+(\.\d+)*)', filename)
    if m:
        return 'V' + m.group(1)
    m = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    if m:
        return m.group(1)
    return ""


def guess_year(filename):
    m = re.search(r'(\d{4})', filename)
    return m.group(1) if m else str(date.today().year)


def format_size(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"


def scan_directory():
    """扫描开发包目录，返回 packages 列表"""
    if not os.path.isdir(DEV_PKG_DIR):
        print(f"❌ 目录不存在: {DEV_PKG_DIR}")
        return []

    packages = []
    existing_ids = set()
    next_id = 1

    # 先读现有 JSON，保留 ID 和手动编辑的字段
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for p in data.get('packages', []):
            existing_ids.add(p['id'])
            packages.append(p)
            try:
                num = int(p['id'].split('-')[-1])
                next_id = max(next_id, num + 1)
            except Exception:
                pass

    existing_filenames = {p['filename'] for p in packages}

    # 扫描目录
    for entry in os.listdir(DEV_PKG_DIR):
        full_path = os.path.join(DEV_PKG_DIR, entry)
        if os.path.isdir(full_path):
            # 文件夹：查找里面的 zip
            for root, dirs, files in os.walk(full_path):
                for f in files:
                    if f.lower().endswith('.zip'):
                        if f in existing_filenames:
                            continue
                        size = os.path.getsize(os.path.join(root, f))
                        pkg_id = f"pkg-{next_id:03d}"
                        next_id += 1
                        rel_path = os.path.join(entry, f).replace('\\', '/')
                        pkg = {
                            "id": pkg_id,
                            "category": guess_category(f),
                            "name": guess_name(f),
                            "year": guess_year(f),
                            "version": guess_version(f),
                            "format": "zip",
                            "filename": f,
                            "path": rel_path,
                            "size": format_size(size),
                            "description": guess_name(f),
                            "download_url": "https://idataaftersales.github.io/idata-docs/"
                                              + urllib.parse.quote(rel_path),
                            "tags": [guess_category(f)]
                        }
                        packages.append(pkg)
                        existing_filenames.add(f)
                        print(f"  ++ 新增(子目录): {entry}/{f}")
            continue
        if not entry.lower().endswith('.zip'):
            continue
        if entry in existing_filenames:
            continue

        size = os.path.getsize(full_path)
        category = guess_category(entry)
        pkg_id = f"pkg-{next_id:03d}"
        next_id += 1

        pkg = {
            "id": pkg_id,
            "category": category,
            "name": guess_name(entry),
            "year": guess_year(entry),
            "version": guess_version(entry),
            "format": "zip",
            "filename": entry,
            "path": "开发包/" + entry,
            "size": format_size(size),
            "description": guess_name(entry),
            "download_url": "https://idataaftersales.github.io/idata-docs/"
                              + urllib.parse.quote("开发包/" + entry),
            "tags": [category]
        }
        packages.append(pkg)
        print(f"  ++ 新增: {entry}")

    return packages


def update_json(packages):
    """写回 dev_packages_catalog.json"""
    data = {
        "version": "1.0",
        "lastUpdated": date.today().isoformat(),
        "description": "iData 开发包清单",
        "packages": packages
    }
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 已更新: {JSON_FILE}")
    print(f"   共 {len(packages)} 个开发包")


def git_push():
    """git add + commit + push"""
    subprocess.run(["git", "add", "dev_packages_catalog.json"], cwd=BASE_DIR, check=False)
    result = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=BASE_DIR)
    if result.returncode == 0:
        print("  ℹ️ 无变更，无需提交")
        return
    msg = f"sync: 自动更新开发包目录 {date.today().isoformat()}"
    subprocess.run(["git", "commit", "-m", msg], cwd=BASE_DIR, check=False)
    subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, check=False)
    print("✅ 已推送到 GitHub")


def main():
    parser = argparse.ArgumentParser(description="同步开发包目录到 JSON")
    parser.add_argument("--push", action="store_true", help="同步后自动 git push")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不写入文件")
    args = parser.parse_args()

    print(f"📂 扫描目录: {DEV_PKG_DIR}")
    packages = scan_directory()

    if args.dry_run:
        print(f"\n[DRY-RUN] 共 {len(packages)} 个开发包，不写入文件")
        for p in packages:
            print(f"  - {p['filename']} ({p['category']})")
        return

    update_json(packages)

    if args.push:
        git_push()

    print(f"\n📋 后续步骤:")
    print(f"   1. 确认 dev_packages_catalog.json 内容正确")
    print(f"   2. 手动推送: cd {BASE_DIR} && git add dev_packages_catalog.json && git commit -m 'sync: 更新开发包' && git push")
    print(f"   3. 或运行: python sync_dev_packages.py --push")

if __name__ == "__main__":
    main()
