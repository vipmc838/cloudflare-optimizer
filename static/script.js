document.addEventListener('DOMContentLoaded', () => {
    const bestIpElem = document.getElementById('best-ip-value');
    const logContentElem = document.getElementById('log-content');
    const configContentElem = document.getElementById('config-content');
    const resultsContentElem = document.getElementById('results-content');
    const runTestBtn = document.getElementById('run-test');

    const API_ENDPOINTS = {
        best_ip: '/api/best_ip',
        results: '/api/results',
        logs: '/api/logs',
        config: '/api/config',
        run_test: '/api/run_test'
    };

    async function fetchData(url, options = {}) {
        try {
            const response = await fetch(url, options);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: `HTTP error! status: ${response.status}` }));
                throw new Error(errorData.error || errorData.message || `HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`Error fetching from ${url}:`, error);
            throw error;
        }
    }

    function renderError(element, message) {
        element.innerHTML = `<p class="error-message">${message}</p>`;
    }

    async function updateBestIP() {
        try {
            const data = await fetchData(API_ENDPOINTS.best_ip);
            bestIpElem.textContent = data.best_ip || "暂未确定";
            bestIpElem.classList.remove('error-message');
        } catch (error) {
            bestIpElem.textContent = "加载失败";
            bestIpElem.classList.add('error-message');
        }
    }

    async function updateResults() {
        try {
            const data = await fetchData(API_ENDPOINTS.results);
            if (data && data.length > 0) {
                const table = document.createElement('table');
                table.id = 'results-table';
                const thead = document.createElement('thead');
                const tbody = document.createElement('tbody');
                
                // Create header
                const headers = Object.keys(data[0]);
                const headerRow = document.createElement('tr');
                headers.forEach(header => {
                    const th = document.createElement('th');
                    th.textContent = header;
                    headerRow.appendChild(th);
                });
                thead.appendChild(headerRow);

                // Create body
                data.forEach(row => {
                    const tr = document.createElement('tr');
                    headers.forEach(header => {
                        const td = document.createElement('td');
                        td.textContent = row[header];
                        tr.appendChild(td);
                    });
                    tbody.appendChild(tr);
                });

                table.appendChild(thead);
                table.appendChild(tbody);
                resultsContentElem.innerHTML = '';
                resultsContentElem.appendChild(table);
            } else {
                resultsContentElem.innerHTML = '<p>暂无优选结果。</p>';
            }
        } catch (error) {
            renderError(resultsContentElem, `加载结果失败: ${error.message}`);
        }
    }

    async function updateLogs() {
        try {
            const data = await fetchData(API_ENDPOINTS.logs);
            logContentElem.textContent = Array.isArray(data) ? data.join('') : data.error || '日志为空。';
            // Auto-scroll to bottom
            logContentElem.scrollTop = logContentElem.scrollHeight;
        } catch (error) {
            logContentElem.textContent = `加载日志失败: ${error.message}`;
            logContentElem.classList.add('error-message');
        }
    }

    async function updateConfig() {
        try {
            const data = await fetchData(API_ENDPOINTS.config);
            configContentElem.textContent = JSON.stringify(data, null, 2);
        } catch (error) {
            configContentElem.textContent = `加载配置失败: ${error.message}`;
            configContentElem.classList.add('error-message');
        }
    }

    runTestBtn.addEventListener('click', async () => {
        runTestBtn.disabled = true;
        runTestBtn.textContent = '正在优选...';
        try {
            const result = await fetchData(API_ENDPOINTS.run_test, { method: 'POST' });
            alert(result.message);
            // Give some time for the backend to process before refreshing
            setTimeout(fetchAllData, 3000); 
        } catch (error) {
            alert(`启动优选任务失败: ${error.message}`);
        } finally {
            runTestBtn.disabled = false;
            runTestBtn.textContent = '立即优选';
        }
    });

    function fetchAllData() {
        updateBestIP();
        updateResults();
        updateLogs();
        updateConfig();
    }

    // Initial load
    fetchAllData();

    // Periodically refresh data every 10 seconds
    setInterval(fetchAllData, 10000);
});
