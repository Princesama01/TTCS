document.addEventListener("DOMContentLoaded", async () => {
    activateNav();
    await refresh();
    setInterval(refresh, 30000);
});

async function refresh() {
    await loadStats();
    await checkEndpoints();
}

async function loadStats() {
    try {
        const s = await API.get("/api/stats");
        document.getElementById("sDocs").textContent = s.documents ?? 0;
        document.getElementById("sChunks").textContent = s.chunks ?? 0;
        document.getElementById("sStatus").textContent = s.status ?? "-";
        document.getElementById("sUpdated").textContent = formatDate(s.last_updated);
    } catch (e) {
        notify("Không tải được stats", "error");
    }
}

async function checkEndpoints() {
    const endpoints = ["/", "/health", "/api/health", "/api/stats", "/api/documents"];
    const wrap = document.getElementById("endpointChecks");
    wrap.innerHTML = "";
    for (const ep of endpoints) {
        let ok = true;
        let detail = "OK";
        try {
            await API.get(ep);
        } catch (e) {
            ok = false;
            detail = e.message;
        }
        const div = document.createElement("div");
        div.className = "item";
        div.innerHTML = `<strong>${ep}</strong> • <span class="badge ${ok ? "success" : "danger"}">${ok ? "OK" : "FAIL"}</span> <span class="muted">${escapeHtml(detail)}</span>`;
        wrap.appendChild(div);
    }
}
