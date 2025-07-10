async function fetchData(url) {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
}

async function updateBestIP() {
    try {
        const data = await fetchData('/api/best_ip');
        document.getElementById('best-ip-value').textContent = data.best_ip || "Not yet determined";
    } catch (error) {
        console.error("Error fetching best IP:", error);
        document.getElementById('best-ip-value').textContent = "Error loading data.";
    }
}

async function updateLogs() {
    try {
        const data = await fetchData('/api/logs');
        document.getElementById('log-content').textContent = Array.isArray(data) ? data.join('') : data.error;
    } catch (error) {
        console.error("Error fetching logs:", error);
        document.getElementById('log-content').textContent = "Error loading logs.";
    }
}

async function updateConfig() {
    try {
        const data = await fetchData('/api/config');
        document.getElementById('config-content').textContent = JSON.stringify(data, null, 2);
    } catch (error) {
        console.error("Error fetching config:", error);
        document.getElementById('config-content').textContent = "Error loading config.";
    }
}

document.getElementById('run-test').addEventListener('click', async () => {
    try {
        const response = await fetch('/api/run_test', { method: 'POST' });
        const result = await response.json();
        alert(result.message);
        // 重新获取最优IP和日志，更新界面
        await updateBestIP();
        await updateLogs();
    } catch (error) {
        console.error("Error running test:", error);
        alert("Error starting IP optimization.");
    }
});

// 初始加载数据
updateBestIP();
updateLogs();
updateConfig();