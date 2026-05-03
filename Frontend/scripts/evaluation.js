function asPct(value) {
    return `${((value || 0) * 100).toFixed(1)}%`;
}

function metricItem(label, value) {
    return `<div class="item"><strong>${escapeHtml(label)}</strong><br><span class="muted">${asPct(value)}</span></div>`;
}

function metricItemRaw(label, value) {
    return `<div class="item"><strong>${escapeHtml(label)}</strong><br><span class="muted">${escapeHtml(String(value || 0))}</span></div>`;
}

function render(data) {
    document.getElementById("evalTimestamp").textContent = data.timestamp || "-";

    const config = data.config || {};
    const rComp = data.rag?.comparison_metrics || {};
    const bComp = data.baseline?.comparison_metrics || {};
    const rRemoved = rComp.removed || {};
    const bRemoved = bComp.removed || {};
    const rAdded = rComp.added || {};
    const bAdded = bComp.added || {};
    const rChanged = rComp.changed || {};
    const bChanged = bComp.changed || {};
    const rOverall = rComp.overall || {};
    const bOverall = bComp.overall || {};
    const nCases = rComp.num_cases || bComp.num_cases || 0;

    document.getElementById("baselineMetrics").innerHTML = [
        metricItemRaw("Method", config.baseline_method || "rule_based_diff"),
        metricItemRaw("So luong case", nCases),
        metricItem("REMOVED F1", bRemoved.f1),
        metricItem("ADDED F1", bAdded.f1),
        metricItem("CHANGED F1", bChanged.f1),
        metricItem("Overall Precision", bOverall.precision),
        metricItem("Overall Recall", bOverall.recall),
        metricItem("Overall F1", bOverall.f1),
    ].join("");

    document.getElementById("ragMetrics").innerHTML = [
        metricItemRaw("Workflow", config.rag_mode || "difflib_semantic_llm"),
        metricItemRaw("LLM model", config.ollama_model || "-"),
        metricItemRaw("So luong case", nCases),
        metricItem("REMOVED F1", rRemoved.f1),
        metricItem("ADDED F1", rAdded.f1),
        metricItem("CHANGED F1", rChanged.f1),
        metricItem("Overall Precision", rOverall.precision),
        metricItem("Overall Recall", rOverall.recall),
        metricItem("Overall F1", rOverall.f1),
    ].join("");
}

async function loadEvaluation() {
    try {
        const data = await API.get("/api/evaluation");
        render(data);
    } catch (_e) {
        const empty = `<div class="item"><span class="muted">Chua co ket qua. Bam "Run Evaluation" de tao du lieu.</span></div>`;
        document.getElementById("baselineMetrics").innerHTML = empty;
        document.getElementById("ragMetrics").innerHTML = empty;
    }
}

async function runEvaluation() {
    const btn = document.getElementById("runEvalBtn");
    btn.disabled = true;
    const old = btn.textContent;
    btn.textContent = "Running...";
    try {
        await API.post("/api/evaluation/run", {});
        notify("Da chay evaluation thanh cong", "success");
        await loadEvaluation();
    } catch (e) {
        notify(e.message || "Khong chay duoc evaluation", "error");
    } finally {
        btn.disabled = false;
        btn.textContent = old;
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    activateNav();
    document.getElementById("runEvalBtn").addEventListener("click", runEvaluation);
    await loadEvaluation();
});
