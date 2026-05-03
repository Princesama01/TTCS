const API_BASE_URL = "http://localhost:5000";

class API {
    static async request(endpoint, options = {}) {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            headers: { "Content-Type": "application/json" },
            ...options
        });
        let data = null;
        try {
            data = await response.json();
        } catch (_e) {
            data = null;
        }
        if (!response.ok) {
            throw new Error((data && (data.detail || data.message)) || `HTTP ${response.status}`);
        }
        return data;
    }

    static get(endpoint) {
        return this.request(endpoint, { method: "GET" });
    }

    static post(endpoint, body) {
        return this.request(endpoint, { method: "POST", body: JSON.stringify(body) });
    }

    static delete(endpoint) {
        return this.request(endpoint, { method: "DELETE" });
    }

    static upload(endpoint, file, onProgress) {
        const formData = new FormData();
        formData.append("file", file);
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open("POST", `${API_BASE_URL}${endpoint}`);
            xhr.timeout = 300000;
            xhr.upload.addEventListener("progress", (e) => {
                if (onProgress && e.lengthComputable) {
                    onProgress((e.loaded / e.total) * 100);
                }
            });
            xhr.onload = () => {
                try {
                    const data = JSON.parse(xhr.responseText || "{}");
                    if (xhr.status >= 200 && xhr.status < 300) {
                        resolve(data);
                    } else {
                        reject(new Error(data.detail || `Upload failed (${xhr.status})`));
                    }
                } catch (_e) {
                    reject(new Error("Invalid response from server"));
                }
            };
            xhr.onerror = () => reject(new Error("Network error"));
            xhr.ontimeout = () => reject(new Error("Request timeout"));
            xhr.send(formData);
        });
    }
}

function ensureToastWrap() {
    let wrap = document.querySelector(".toast-wrap");
    if (!wrap) {
        wrap = document.createElement("div");
        wrap.className = "toast-wrap";
        document.body.appendChild(wrap);
    }
    return wrap;
}

function notify(message, type = "info") {
    const wrap = ensureToastWrap();
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.textContent = message;
    wrap.appendChild(el);
    setTimeout(() => {
        el.remove();
    }, 3500);
}

function formatDate(v) {
    if (!v) return "-";
    return new Date(v).toLocaleString("vi-VN");
}

function formatSize(bytes) {
    if (!bytes && bytes !== 0) return "-";
    const units = ["B", "KB", "MB", "GB"];
    let i = 0;
    let value = bytes;
    while (value >= 1024 && i < units.length - 1) {
        value /= 1024;
        i += 1;
    }
    return `${value.toFixed(i === 0 ? 0 : 2)} ${units[i]}`;
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = String(str ?? "");
    return div.innerHTML;
}

function debounce(fn, wait) {
    let t = null;
    return (...args) => {
        clearTimeout(t);
        t = setTimeout(() => fn(...args), wait);
    };
}

async function copyText(text) {
    await navigator.clipboard.writeText(text);
    notify("Đã copy", "success");
}

function activateNav() {
    const page = location.pathname.split("/").pop();
    document.querySelectorAll(".nav a").forEach((a) => {
        if (a.getAttribute("href") === page) {
            a.classList.add("active");
        }
    });
}

window.API = API;
window.API_BASE_URL = API_BASE_URL;
window.notify = notify;
window.formatDate = formatDate;
window.formatSize = formatSize;
window.escapeHtml = escapeHtml;
window.debounce = debounce;
window.copyText = copyText;
window.activateNav = activateNav;
