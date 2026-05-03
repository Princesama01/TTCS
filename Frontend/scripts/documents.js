let allDocs = [];
const DEFAULT_API_BASE_URL = `${window.location.protocol}//${window.location.hostname}:5000`;

function getApiBaseUrl() {
    return window.API_BASE_URL || DEFAULT_API_BASE_URL;
}

function setDocxMessage(target, message) {
    target.innerHTML = `<div class="muted">${escapeHtml(message)}</div>`;
}

document.addEventListener("DOMContentLoaded", async () => {
    activateNav();
    document.getElementById("reloadBtn").addEventListener("click", loadDocs);
    document.getElementById("searchInput").addEventListener("input", debounce(filterDocs, 250));
    await loadDocs();
});

async function loadDocs() {
    try {
        const res = await API.get("/api/documents");
        allDocs = res.documents || [];
        renderDocs(allDocs);
    } catch (e) {
        notify("Không tải được documents", "error");
    }
}

function filterDocs() {
    const q = document.getElementById("searchInput").value.trim().toLowerCase();
    if (!q) {
        renderDocs(allDocs);
        return;
    }
    renderDocs(allDocs.filter((d) => d.name.toLowerCase().includes(q) || d.id.toLowerCase().includes(q)));
}

function renderDocs(docs) {
    const list = document.getElementById("documentsList");
    list.innerHTML = docs.map((d) => `
        <div class="item">
            <h4>${escapeHtml(d.name)}</h4>
            <div class="muted">${d.id} • ${d.file_type} • ${formatSize(d.size)} • ${formatDate(d.created_at)}</div>
            <div class="row-wrap" style="margin-top:8px;">
                <span class="badge ${d.status === "ready" ? "success" : "warning"}">${d.status}</span>
                ${d.has_original_file ? `<button class="btn" onclick="previewOriginalFile('${d.id}')">Mở file gốc</button>` : ""}
                <button class="btn" onclick="loadClauses('${d.id}')">Xem clauses</button>
                <button class="btn btn-danger" onclick="deleteDoc('${d.id}')">Xóa</button>
            </div>
        </div>
    `).join("");
}

async function loadClauses(docId) {
    const target = document.getElementById("clausesList");
    target.innerHTML = "<div class='item'>Loading...</div>";
    try {
        const res = await API.get(`/api/documents/${docId}/clauses`);
        const clauses = res.clauses || [];
        if (!clauses.length) {
            target.innerHTML = "<div class='item'>Không có clauses</div>";
            return;
        }
        target.innerHTML = clauses.slice(0, 30).map((c) => `
            <div class="item">
                <h4>Điều ${escapeHtml(c.number)}</h4>
                <div class="mono">${escapeHtml(c.content)}</div>
            </div>
        `).join("");
    } catch (e) {
        target.innerHTML = `<div class="item">${escapeHtml(e.message)}</div>`;
    }
}

async function deleteDoc(docId) {
    if (!confirm(`Xóa ${docId}?`)) return;
    try {
        await API.delete(`/api/documents/${docId}`);
        notify("Đã xóa document", "success");
        await loadDocs();
    } catch (e) {
        notify(e.message, "error");
    }
}

async function previewOriginalFile(docId) {
    const doc = allDocs.find((d) => d.id === docId);
    if (!doc || !doc.has_original_file) {
        notify("Tài liệu chưa có file gốc", "error");
        return;
    }

    const frame = document.getElementById("originalFileFrame");
    const docxView = document.getElementById("originalFileDocxView");
    const link = document.getElementById("originalFileOpenLink");

    try {
        const fileMetaRes = await API.get(`/api/documents/${encodeURIComponent(docId)}/file`);
        const url = `${getApiBaseUrl()}${fileMetaRes.file.content_url}`;
        const contentType = String(fileMetaRes.file.content_type || "").toLowerCase();
        const fileName = String(fileMetaRes.file.name || "").toLowerCase();
        const isDocx = contentType.includes("wordprocessingml") || fileName.endsWith(".docx");

        link.href = url;
        link.textContent = `Mở tab mới: ${doc.name}`;

        if (isDocx) {
            frame.classList.add("hidden");
            frame.src = "about:blank";
            docxView.classList.remove("hidden");
            setDocxMessage(docxView, "Đang render DOCX...");

            if (!window.mammoth || typeof window.mammoth.convertToHtml !== "function") {
                setDocxMessage(docxView, "Trình render DOCX chưa sẵn sàng. Hãy mở ở tab mới.");
                return;
            }

            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const arrayBuffer = await response.arrayBuffer();
            const result = await window.mammoth.convertToHtml({ arrayBuffer });
            docxView.innerHTML = result.value || `<div class="muted">Không có nội dung hiển thị.</div>`;
            return;
        }

        docxView.classList.add("hidden");
        frame.classList.remove("hidden");
        frame.src = url;
    } catch (e) {
        frame.classList.add("hidden");
        frame.src = "about:blank";
        docxView.classList.remove("hidden");
        setDocxMessage(docxView, "Không hiển thị được tài liệu này. Hãy mở ở tab mới.");
    }
}

window.loadClauses = loadClauses;
window.previewOriginalFile = previewOriginalFile;
window.deleteDoc = deleteDoc;
