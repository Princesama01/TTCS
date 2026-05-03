let currentUploadId = null;

document.addEventListener("DOMContentLoaded", () => {
    activateNav();
    document.getElementById("uploadBtn").addEventListener("click", handleUpload);
});

async function handleUpload() {
    const file = document.getElementById("fileInput").files[0];
    if (!file) {
        notify("Vui lòng chọn file", "error");
        return;
    }

    const progress = document.getElementById("uploadProgress");
    const text = document.getElementById("uploadText");
    const result = document.getElementById("uploadResult");

    try {
        const res = await API.upload("/api/upload", file, (p) => {
            progress.style.width = `${p}%`;
            text.textContent = `${Math.round(p)}%`;
        });
        result.textContent = `Upload thành công: ${res.doc_id}`;
        currentUploadId = res.upload_id;
        notify("Upload thành công, đang xử lý pipeline", "success");
        await pollStatus();
    } catch (e) {
        notify(e.message, "error");
    }
}

async function pollStatus() {
    const container = document.getElementById("pipelineStatus");
    for (let i = 0; i < 120; i += 1) {
        const res = await API.get(`/api/upload/status/${currentUploadId}`);
        const status = res.pipeline_status || {};
        container.innerHTML = Object.keys(status).map((k) => `<div class="item"><strong>${k}</strong>: ${status[k]}</div>`).join("");
        const done = Object.values(status).every((v) => v === "completed");
        if (done) {
            notify("Pipeline hoàn tất", "success");
            return;
        }
        await new Promise((r) => setTimeout(r, 1500));
    }
    notify("Pipeline timeout", "error");
}
