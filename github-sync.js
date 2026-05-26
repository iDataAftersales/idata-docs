// github-sync.js - iData 设备说明书知识库 GitHub 同步
const GITHUB_TOKEN_KEY = "github_token";
const GITHUB_REPO = "iDataAftersales/idata-docs";
const GITHUB_BRANCH = "main";
const GITHUB_CATALOG = "knowledge_base_catalog.json";

function kb_saveDB() {
    try { localStorage.setItem("kb_db_backup", JSON.stringify(DB)); } catch(e) {}
}

function kb_loadToken() { return localStorage.getItem(GITHUB_TOKEN_KEY) || ""; }
function kb_saveToken(t) {
    if (t) localStorage.setItem(GITHUB_TOKEN_KEY, t);
    else { localStorage.removeItem(GITHUB_TOKEN_KEY); if(typeof showToast==="function") showToast("Token 已清除"); }
    kb_initSaveBtn();
}

async function kb_saveToGitHub() {
    const token = kb_loadToken();
    if (!token) { if(typeof showSettings==="function") showSettings(); return; }
    const btn = document.getElementById("btnSaveGitHub");
    if (btn) { btn.disabled = true; btn.textContent = "保存中..."; }
    try {
        const catalog = { version:"1.0", lastUpdated:new Date().toISOString().split("T")[0], description:"iData 设备说明书知识库", documents:DB };
        const bodyStr = JSON.stringify(catalog, null, 2);
        const b64 = btoa(unescape(encodeURIComponent(bodyStr)));
        let sha = "";
        try {
            const r = await fetch("https://api.github.com/repos/" + GITHUB_REPO + "/contents/" + GITHUB_CATALOG + "?ref=" + GITHUB_BRANCH, {
                headers: { "Authorization":"token " + token, "Accept":"application/vnd.github.v3+json" }
            });
            if (r.ok) sha = (await r.json()).sha;
        } catch(e) {}
        const putBody = { message:"chore: update knowledge base", content:b64, branch:GITHUB_BRANCH };
        if (sha) putBody.sha = sha;
        const r2 = await fetch("https://api.github.com/repos/" + GITHUB_REPO + "/contents/" + GITHUB_CATALOG, {
            method: "PUT",
            headers: { "Authorization":"token " + token, "Content-Type":"application/json", "Accept":"application/vnd.github.v3+json" },
            body: JSON.stringify(putBody)
        });
        if (r2.ok) { if(typeof showToast==="function") showToast("已保存到 GitHub!"); }
        else { const err = await r2.json(); if(typeof showToast==="function") showToast("保存失败: " + (err.message||r2.status)); }
    } catch(e) { if(typeof showToast==="function") showToast("保存失败: " + e.message); }
    finally { if(btn) { btn.disabled=false; btn.textContent="保存到 GitHub"; } }
}

function kb_showSettings() {
    let m = document.getElementById("settingsModal");
    if (!m) {
        m = document.createElement("div"); m.id = "settingsModal"; m.className = "modal";
        m.innerHTML = "<div class='modal-content' style='max-width:420px'><div class='modal-header'><h3>GitHub 设置</h3><button class='close-btn' onclick='kb_hideSettings()'>x</button></div><div style='padding:20px'><label>GitHub Token（需 repo 权限）<br><input type='password' id='tokenInput' placeholder='ghp_xxx' style='width:100%;padding:8px;margin:8px 0;border:1px solid var(--border);border-radius:6px'></label><div style='font-size:0.8em;color:var(--text-light);margin-bottom:12px'>获取 Token: <a href='https://github.com/settings/tokens/new?scopes=repo&description=idata-docs' target='_blank'>点此生成</a>（勾选 repo）</div><div style='display:flex;gap:10px'><button class='btn btn-primary' onclick='kb_doSaveToken()'>保存 Token</button><button class='btn btn-outline' onclick='kb_hideSettings()'>取消</button></div></div></div>";
        document.body.appendChild(m);
    }
    const ti = document.getElementById("tokenInput");
    if (ti) ti.value = kb_loadToken();
    m.classList.add("active");
}
function kb_hideSettings() { document.getElementById("settingsModal")?.classList.remove("active"); }
function kb_doSaveToken() {
    const t = document.getElementById("tokenInput").value.trim();
    if (!t) { if(typeof showToast==="function") showToast("请输入 Token"); return; }
    kb_saveToken(t);
    if(typeof showToast==="function") showToast("Token 已保存");
    kb_hideSettings();
}
function kb_initSaveBtn() {
    const b = document.getElementById("btnSaveGitHub");
    if (b) b.disabled = !kb_loadToken();
}

// 暴露全局函数
window.showSettings = kb_showSettings;
window.hideSettings = kb_hideSettings;
window.doSaveToken = kb_doSaveToken;
window.saveToGitHub = kb_saveToGitHub;
window.initSaveBtn = kb_initSaveBtn;
window.saveDB = kb_saveDB;

// URL Token 检测
function tryLoadTokenFromURL() {
    const params = new URLSearchParams(window.location.search);
    const t = params.get("token");
    if (t && t.startsWith("ghp_")) {
        localStorage.setItem(GITHUB_TOKEN_KEY, t);
        if(typeof showToast==="function") showToast("Token 已从 URL 自动配置");
        window.history.replaceState({}, document.title, window.location.pathname);
    }
}

// localStorage 恢复
function tryRestoreDB() {
    try {
        const saved = localStorage.getItem("kb_db_backup");
        if (saved) { DB = JSON.parse(saved); console.log("[KB] 从 localStorage 恢复", DB.length, "条"); }
    } catch(e) { console.warn("[KB] localStorage 恢复失败", e); }
}

window.tryLoadTokenFromURL = tryLoadTokenFromURL;
window.tryRestoreDB = tryRestoreDB;

document.addEventListener("DOMContentLoaded", function(){ kb_initSaveBtn(); });