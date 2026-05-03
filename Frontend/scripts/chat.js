document.addEventListener("DOMContentLoaded", () => {
    activateNav();
    document.getElementById("askBtn").addEventListener("click", ask);
});

async function ask() {
    const question = document.getElementById("question").value.trim();
    if (!question) return notify("Nhập câu hỏi", "error");
    const body = {
        question,
        use_context: document.getElementById("useContext").value === "true"
    };
    const articleNo = document.getElementById("articleNo").value.trim();
    const version = document.getElementById("version").value.trim();
    if (articleNo) body.article_no = articleNo;
    if (version) body.version = version;

    document.getElementById("answer").textContent = "Loading...";
    document.getElementById("citations").innerHTML = "";
    try {
        const res = await API.post("/api/ask", body);
        document.getElementById("answer").textContent = res.answer || "";
        const citations = res.citations || [];
        document.getElementById("citations").innerHTML = citations.map((c, idx) => `
            <div class="item">
                <h4>#${idx + 1} • ${(c.score * 100).toFixed(1)}%</h4>
                <div class="muted">${escapeHtml(c.version || "-")} • Điều ${escapeHtml(c.article_no || "-")} • Trang ${escapeHtml(c.page_number || "-")}</div>
                <p class="mono">${escapeHtml(c.content || "")}</p>
                <div class="muted">${escapeHtml(c.structure_path || "")}</div>
            </div>
        `).join("");
    } catch (e) {
        document.getElementById("answer").textContent = e.message;
    }
}
