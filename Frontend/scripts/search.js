document.addEventListener("DOMContentLoaded", () => {
    activateNav();
    document.getElementById("searchBtn").addEventListener("click", handleSearch);
    document.getElementById("queryInput").addEventListener("keypress", (e) => {
        if (e.key === "Enter") handleSearch();
    });
});

async function handleSearch() {
    const query = document.getElementById("queryInput").value.trim();
    if (!query) return notify("Nhập truy vấn", "error");
    const body = {
        query,
        vector_name: document.getElementById("vectorName").value,
        top_k: Number(document.getElementById("topK").value || 5)
    };
    const version = document.getElementById("version").value.trim();
    if (version) body.version = version;

    const results = document.getElementById("results");
    results.innerHTML = "<div class='item'>Loading...</div>";

    try {
        const res = await API.post("/api/search", body);
        const list = res.results || [];
        if (!list.length) {
            results.innerHTML = "<div class='item'>Không có kết quả</div>";
            return;
        }
        results.innerHTML = list.map((r, idx) => `
            <div class="item">
                <h4>#${idx + 1} • score ${(r.score * 100).toFixed(1)}%</h4>
                <div class="muted">${escapeHtml(r.version || "-")} • Điều ${escapeHtml(r.article_no || "-")} • ${escapeHtml(r.chunk_type || "-")}</div>
                <p class="mono">${escapeHtml(r.content)}</p>
                <div class="muted">${escapeHtml(r.structure_path || "")}</div>
            </div>
        `).join("");
    } catch (e) {
        results.innerHTML = `<div class='item'>${escapeHtml(e.message)}</div>`;
    }
}
