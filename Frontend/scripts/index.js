document.addEventListener("DOMContentLoaded", async () => {
    activateNav();
    await refreshDashboard();
    setInterval(refreshDashboard, 30000);
});

function setBadge(id, text, kind) {
    const el = document.getElementById(id);
    el.textContent = text;
    el.className = `badge ${kind}`;
}

async function refreshDashboard() {
    try {
        const health = await API.get("/health");
        setBadge("apiStatus", health.status || "unknown", health.status === "healthy" ? "success" : "danger");
        setBadge("pipelineStatus", health.pipeline || "unknown", health.pipeline === "ready" ? "success" : "warning");
        const ollamaState = health.ollama || "unavailable";
        setBadge("ollamaStatus", ollamaState, ollamaState === "unavailable" ? "warning" : "success");
    } catch (e) {
        setBadge("apiStatus", "offline", "danger");
        setBadge("pipelineStatus", "offline", "danger");
        setBadge("ollamaStatus", "offline", "danger");
    }

    try {
        const stats = await API.get("/api/stats");
        document.getElementById("documentsCount").textContent = stats.documents ?? 0;
        document.getElementById("chunksCount").textContent = stats.chunks ?? 0;
        document.getElementById("updatedAt").textContent = formatDate(stats.last_updated);
    } catch (e) {
        notify("Không tải được stats", "error");
    }
}
