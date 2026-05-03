let docs = [];
let lastCompareResult = null;
const DEFAULT_API_BASE_URL = `${window.location.protocol}//${window.location.hostname}:5000`;

function getApiBaseUrl() {
    return window.API_BASE_URL || DEFAULT_API_BASE_URL;
}

document.addEventListener("DOMContentLoaded", async () => {
    activateNav();
    document.getElementById("compareBtn").addEventListener("click", runCompare);

    // Tab switching
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.addEventListener("click", () => switchTab(btn.dataset.tab));
    });

    await loadDocs();
});

async function loadDocs() {
    try {
        const res = await API.get("/api/documents");
        docs = res.documents || [];
        const options = docs.map((d) => `<option value="${d.id}">${escapeHtml(d.name)} (${d.id})</option>`).join("");
        document.getElementById("doc1").innerHTML = options;
        document.getElementById("doc2").innerHTML = options;
        if (docs.length > 1) {
            document.getElementById("doc2").selectedIndex = 1;
        }
    } catch (_e) {
        notify("Không tải được documents", "error");
    }
}

function buildPayload() {
    return {
        doc_id_1: document.getElementById("doc1").value,
        doc_id_2: document.getElementById("doc2").value,
        mode: document.getElementById("mode").value,
        semantic_threshold: Number(document.getElementById("semanticThreshold").value),
        candidate_threshold: Number(document.getElementById("candidateThreshold").value),
        llm_confidence_threshold: Number(document.getElementById("llmConfidenceThreshold").value),
        max_segments: Number(document.getElementById("maxSegments").value),
        changed_only: document.getElementById("changedOnly").checked
    };
}

function normalizeChangeType(type) {
    if (type === "changed_meaning") return "modified";
    return type || "modified";
}

function renderDocxMessage(target, message) {
    target.innerHTML = `<div class="muted">${escapeHtml(message)}</div>`;
}

async function renderDocumentFile(docId, frameId, docxViewId, linkId, label) {
    const frame = document.getElementById(frameId);
    const docxView = document.getElementById(docxViewId);
    const link = document.getElementById(linkId);

    frame.classList.remove("hidden");
    docxView.classList.add("hidden");

    if (!docId) {
        frame.src = "about:blank";
        renderDocxMessage(docxView, `${label} chưa được chọn`);
        docxView.classList.remove("hidden");
        frame.classList.add("hidden");
        link.href = "#";
        link.textContent = `${label} chưa được chọn`;
        return;
    }

    try {
        const fileMetaRes = await API.get(`/api/documents/${encodeURIComponent(docId)}/file`);
        const contentUrl = `${getApiBaseUrl()}${fileMetaRes.file.content_url}`;
        const contentType = String(fileMetaRes.file.content_type || "").toLowerCase();
        const fileName = String(fileMetaRes.file.name || "").toLowerCase();
        const isDocx = contentType.includes("wordprocessingml") || fileName.endsWith(".docx");

        link.href = contentUrl;
        link.textContent = `Mở ${label} ở tab mới`;

        if (isDocx) {
            frame.src = "about:blank";
            frame.classList.add("hidden");
            docxView.classList.remove("hidden");
            renderDocxMessage(docxView, `Đang render ${label}...`);

            if (!window.mammoth || typeof window.mammoth.convertToHtml !== "function") {
                renderDocxMessage(docxView, "Trình render DOCX chưa sẵn sàng. Hãy mở ở tab mới.");
                return;
            }

            const response = await fetch(contentUrl);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const arrayBuffer = await response.arrayBuffer();
            const result = await window.mammoth.convertToHtml({ arrayBuffer });
            docxView.innerHTML = result.value || `<div class="muted">${label} không có nội dung hiển thị.</div>`;
            return;
        }

        frame.src = contentUrl;
    } catch (e) {
        frame.src = "about:blank";
        frame.classList.add("hidden");
        docxView.classList.remove("hidden");
        renderDocxMessage(docxView, `${label} không hiển thị được. Hãy mở ở tab mới.`);
    }
}

function renderComparisonDetail(change) {
    const wrap = document.getElementById("resultDetail");
    const title = document.getElementById("resultDetailTitle");
    const body = document.getElementById("resultDetailBody");
    const detail = lastCompareResult?.change_details?.[change.id] || {};
    const source = detail.source || "";
    const target = detail.target || "";
    title.textContent = `${change.title || change.type} | ${change.method || "-"}`;
    body.textContent =
        `SOURCE:\n${source || "(none)"}\n\n` +
        `TARGET:\n${target || "(none)"}\n\n` +
        `confidence: ${Number(change.confidence || 0).toFixed(3)}\n` +
        `reason: ${detail.reason || "-"}`;
    wrap.classList.remove("hidden");
}

function renderResultsList(filterType = "all") {
    const wrap = document.getElementById("resultsList");
    const changes = lastCompareResult?.changes || [];

    let filtered = changes;
    if (filterType === "changes") {
        filtered = changes.filter(c => normalizeChangeType(c.type) === "modified");
    } else if (filterType === "added") {
        filtered = changes.filter(c => normalizeChangeType(c.type) === "added");
    } else if (filterType === "removed") {
        filtered = changes.filter(c => normalizeChangeType(c.type) === "removed");
    }

    if (!filtered.length) {
        wrap.innerHTML = "<div class='item' style='text-align:center; padding: 20px; color: var(--muted);'>Không có thay đổi</div>";
        return filtered;
    }

    wrap.innerHTML = filtered.map((c, idx) => {
        const normalizedType = normalizeChangeType(c.type);
        const typeLabel = {
            "added": "Thêm mới",
            "removed": "Xóa bỏ",
            "modified": "Sửa đổi"
        }[normalizedType] || normalizedType;

        const preview = (c.source_preview || c.target_preview || "").substring(0, 60);
        return `
            <div class="result-item ${normalizedType}" data-change-id="${escapeHtml(c.id)}">
                <h4 class="result-item-title">${typeLabel}</h4>
                <p class="result-item-subtitle">
                    ${escapeHtml(c.method || "-")} | Confidence: ${Number(c.confidence || 0).toFixed(3)}
                </p>
                <p class="result-item-preview">${escapeHtml(preview)}${preview.length > 60 ? '...' : ''}</p>
            </div>
        `;
    }).join("");

    document.querySelectorAll(".result-item[data-change-id]").forEach((el) => {
        el.addEventListener("click", () => {
            const id = el.getAttribute("data-change-id");
            const change = (lastCompareResult?.changes || []).find((c) => c.id === id);
            if (!change) return;
            renderComparisonDetail(change);
        });
    });
    return filtered;
}

function switchTab(tabType) {
    // Update active tab button
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.classList.remove("active");
        if (btn.dataset.tab === tabType) {
            btn.classList.add("active");
        }
    });

    // Hide detail when switching tabs
    document.getElementById("resultDetail").classList.add("hidden");

    renderResultsList(tabType);
}

function renderSummary() {
    const summaryStats = document.getElementById("summaryStats");
    const summaryTags = document.getElementById("summaryTags");
    const changes = lastCompareResult?.changes || [];
    const modified = changes.filter((c) => normalizeChangeType(c.type) === "modified").length;
    const added = changes.filter((c) => normalizeChangeType(c.type) === "added").length;
    const removed = changes.filter((c) => normalizeChangeType(c.type) === "removed").length;
    const highConfidence = changes.filter((c) => Number(c.confidence || 0) >= 0.8).length;
    const methods = new Set(changes.map((c) => c.method).filter(Boolean));

    summaryStats.textContent = `${changes.length} thay đổi được phát hiện`;
    summaryTags.innerHTML = `
        <span class="tag tag-high">${modified} Sửa đổi</span>
        <span class="tag tag-same">${added} Thêm mới</span>
        <span class="tag tag-medium">${removed} Xóa bỏ</span>
        <span class="tag tag-llm">${highConfidence} Tin cậy cao</span>
        <span class="tag">${methods.size} phương pháp</span>
    `;
}

async function renderCompareView() {
    if (!lastCompareResult) {
        return;
    }

    await Promise.all([
        renderDocumentFile(lastCompareResult?.doc1_info?.id, "doc1FileFrame", "doc1DocxView", "doc1FileOpen", "VB1"),
        renderDocumentFile(lastCompareResult?.doc2_info?.id, "doc2FileFrame", "doc2DocxView", "doc2FileOpen", "VB2")
    ]);
    document.getElementById("resultDetail").classList.add("hidden");

    // Update summary and tab counts
    const changes = lastCompareResult.changes || [];
    const modified = changes.filter((c) => normalizeChangeType(c.type) === "modified").length;
    const added = changes.filter((c) => normalizeChangeType(c.type) === "added").length;
    const removed = changes.filter((c) => normalizeChangeType(c.type) === "removed").length;
    renderSummary();

    // Update tab counts
    document.querySelectorAll(".tab-btn").forEach(btn => {
        if (btn.dataset.tab === "changes") {
            btn.querySelector(".tab-count").textContent = modified;
        } else if (btn.dataset.tab === "added") {
            btn.querySelector(".tab-count").textContent = added;
        } else if (btn.dataset.tab === "removed") {
            btn.querySelector(".tab-count").textContent = removed;
        }
    });

    // Render initial results list (default to "changes" tab)
    const firstFiltered = renderResultsList("changes");
    if (firstFiltered && firstFiltered.length > 0) {
        renderComparisonDetail(firstFiltered[0]);
    }
}

async function runCompare() {
    const payload = buildPayload();
    if (!payload.doc_id_1 || !payload.doc_id_2) {
        return notify("Chọn đủ 2 documents", "error");
    }
    if (payload.doc_id_1 === payload.doc_id_2) {
        return notify("Hai documents phải khác nhau", "error");
    }

    try {
        const res = await API.post("/api/compare-documents", payload);
        lastCompareResult = res;
        document.getElementById("compareViewWrap").classList.remove("hidden");
        await renderCompareView();
    } catch (e) {
        notify(e.message || "Compare thất bại", "error");
    }
}
