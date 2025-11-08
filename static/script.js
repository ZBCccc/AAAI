// 全局变量
let autoRefreshInterval = null;
let isAutoRefreshEnabled = true;

// DOM元素
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const refreshBtn = document.getElementById('refreshBtn');
const clearBtn = document.getElementById('clearBtn');
const autoRefreshCheckbox = document.getElementById('autoRefresh');
const latestCard = document.getElementById('latestCard');
const resultsContainer = document.getElementById('resultsContainer');

// 使用marked.js进行Markdown渲染

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    
    // 延迟测试Markdown渲染功能，确保marked.js已加载
    setTimeout(() => {
        try {
            testMarkdownRendering();
            console.log('✅ Markdown渲染功能正常工作');
        } catch (error) {
            console.error('❌ Markdown渲染功能测试失败:', error);
        }
    }, 1000);
});

function initializeApp() {
    // 绑定事件监听器
    refreshBtn.addEventListener('click', refreshData);
    clearBtn.addEventListener('click', clearHistory);
    autoRefreshCheckbox.addEventListener('change', toggleAutoRefresh);
    
    // 初始加载数据
    refreshData();
    
    // 启动自动刷新
    startAutoRefresh();
    
    // 检查服务器状态
    checkServerHealth();
}

// 检查服务器健康状态
async function checkServerHealth() {
    try {
        const response = await fetch('/api/health');
        if (response.ok) {
            updateStatus(true, '已连接');
        } else {
            updateStatus(false, '服务器错误');
        }
    } catch (error) {
        updateStatus(false, '连接失败');
        console.error('健康检查失败:', error);
    }
}

// 更新连接状态
function updateStatus(isConnected, message) {
    if (isConnected) {
        statusDot.classList.add('connected');
        statusText.textContent = message;
    } else {
        statusDot.classList.remove('connected');
        statusText.textContent = message;
    }
}

// 刷新数据
async function refreshData() {
    try {
        // 显示加载状态
        refreshBtn.innerHTML = '<span class="loading"></span> 刷新中...';
        refreshBtn.disabled = true;
        
        // 获取最新结果
        await loadLatestResult();
        
        // 获取所有历史记录
        await loadAllResults();
        
        updateStatus(true, '已连接');
    } catch (error) {
        console.error('刷新数据失败:', error);
        updateStatus(false, '刷新失败');
    } finally {
        // 恢复按钮状态
        refreshBtn.innerHTML = '🔄 刷新';
        refreshBtn.disabled = false;
    }
}

// 加载最新结果
async function loadLatestResult() {
    try {
        const response = await fetch('/api/results/latest');
        const data = await response.json();
        
        if (data.result) {
            displayLatestResult(data.result);
        } else {
            latestCard.innerHTML = '<div class="no-data">暂无数据，等待分析结果...</div>';
        }
    } catch (error) {
        console.error('加载最新结果失败:', error);
        latestCard.innerHTML = '<div class="no-data">加载失败，请检查网络连接</div>';
    }
}

// 加载所有结果
async function loadAllResults() {
    try {
        const response = await fetch('/api/results');
        const data = await response.json();
        
        if (data.results && data.results.length > 0) {
            displayResults(data.results);
        } else {
            resultsContainer.innerHTML = '<div class="no-data">暂无历史记录</div>';
        }
    } catch (error) {
        console.error('加载历史记录失败:', error);
        resultsContainer.innerHTML = '<div class="no-data">加载失败，请检查网络连接</div>';
    }
}

// 显示最新结果
function displayLatestResult(result) {
    const resultHtml = createResultCard(result, true);
    latestCard.innerHTML = resultHtml;
}

// 显示所有结果
function displayResults(results) {
    if (results.length === 0) {
        resultsContainer.innerHTML = '<div class="no-data">暂无历史记录</div>';
        return;
    }
    
    // 按时间倒序排列
    const sortedResults = results.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    const resultsHtml = sortedResults.map(result => createResultCard(result, false)).join('');
    resultsContainer.innerHTML = resultsHtml;
}

// 创建结果卡片HTML
function createResultCard(result, isLatest = false) {
    const timestamp = formatTimestamp(result.timestamp);
    const typeIcon = '📸';
    const typeClass = 'screenshot';
    const latestClass = isLatest ? 'latest' : '';
    const cardId = `card_${result.id}_${Date.now()}`;
    
    let originalContentHtml = '';
    
    // 根据类型显示原始内容（默认折叠）
    if (result.image_path) {
        originalContentHtml = `
            <div class="original-content-section">
                <div class="original-content-header" onclick="toggleOriginalContent('${cardId}_image')">
                    <span>📸 查看原始截图</span>
                    <button class="original-content-toggle" id="${cardId}_image_toggle">▶</button>
                </div>
                <div class="original-content-body" id="${cardId}_image_content" style="display: none;">
                    <img src="/web_data/${result.image_path}" alt="截图" class="result-image" onerror="this.style.display='none'">
                </div>
            </div>
        `;
    }
    
    const deleteButton = !isLatest ? `<button class="delete-btn" onclick="deleteResult('${result.id}')">🗑️ 删除</button>` : '';
    
    return `
        <div class="result-card ${latestClass}">
            <div class="result-header">
                <div class="result-type ${typeClass}">
                    ${typeIcon} 截图分析
                </div>
                <div style="display: flex; gap: 10px; align-items: center;">
                    <span class="result-timestamp">${timestamp}</span>
                    ${deleteButton}
                </div>
            </div>
            
            <!-- 原始内容 - 默认折叠 -->
            ${originalContentHtml}
            
            <!-- 思考过程 - 默认折叠 -->
            <div class="think-process-section">
                ${processThinkTagsOnly(result.analysis)}
            </div>
            
            <!-- AI分析结果 - 直接展示 -->
            <div class="ai-analysis-main">
                <div class="analysis-answer">
                    ${removeThinkTags(result.analysis)}
                </div>
            </div>
        </div>
    `;
}

// 删除结果
async function deleteResult(resultId) {
    if (!confirm('确定要删除这条记录吗？')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/results/${resultId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            // 刷新数据
            await refreshData();
        } else {
            alert('删除失败，请重试');
        }
    } catch (error) {
        console.error('删除结果失败:', error);
        alert('删除失败，请检查网络连接');
    }
}

// 清空历史记录
async function clearHistory() {
    if (!confirm('确定要清空所有历史记录吗？此操作不可恢复！')) {
        return;
    }
    
    try {
        // 获取所有结果
        const response = await fetch('/api/results');
        const data = await response.json();
        
        if (data.results && data.results.length > 0) {
            // 逐个删除
            for (const result of data.results) {
                await fetch(`/api/results/${result.id}`, { method: 'DELETE' });
            }
        }
        
        // 刷新显示
        await refreshData();
        alert('历史记录已清空');
    } catch (error) {
        console.error('清空历史记录失败:', error);
        alert('清空失败，请重试');
    }
}

// 切换自动刷新
function toggleAutoRefresh() {
    isAutoRefreshEnabled = autoRefreshCheckbox.checked;
    
    if (isAutoRefreshEnabled) {
        startAutoRefresh();
    } else {
        stopAutoRefresh();
    }
}

// 启动自动刷新
function startAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
    
    if (isAutoRefreshEnabled) {
        autoRefreshInterval = setInterval(refreshData, 5000); // 每5秒刷新一次
    }
}

// 停止自动刷新
function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

// 格式化时间戳
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// HTML转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 页面可见性变化处理
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        stopAutoRefresh();
    } else if (isAutoRefreshEnabled) {
        startAutoRefresh();
        refreshData(); // 立即刷新一次
    }
});

// 窗口焦点变化处理
window.addEventListener('focus', function() {
    if (isAutoRefreshEnabled) {
        refreshData();
    }
});

// 折叠/展开AI分析结果
function toggleCollapse(contentId) {
    const content = document.getElementById(contentId + '_content');
    const toggle = document.getElementById(contentId + '_toggle');
    
    if (content && toggle) {
        content.classList.toggle('expanded');
        toggle.classList.toggle('expanded');
    }
}

// 折叠/展开原始内容
function toggleOriginalContent(contentId) {
    const content = document.getElementById(contentId + '_content');
    const toggle = document.getElementById(contentId + '_toggle');
    
    if (content && toggle) {
        const isCollapsed = content.style.display === 'none';
        content.style.display = isCollapsed ? 'block' : 'none';
        toggle.textContent = isCollapsed ? '▼' : '▶';
    }
}

// 处理<think>标签，使其默认折叠
function processThinkTags(text) {
    if (!text) return '';
    
    // 使用正则表达式匹配<think>标签
    const thinkRegex = /<think>([\s\S]*?)<\/think>/g;
    let processedText = text;
    let thinkIndex = 0;
    
    processedText = processedText.replace(thinkRegex, (match, content) => {
        thinkIndex++;
        const thinkId = `think-${Date.now()}-${thinkIndex}`;
        return `
            <div class="think-collapsible-section">
                <div class="think-collapsible-header" onclick="toggleThinkCollapse('${thinkId}')">
                    <span>🤔 思考过程</span>
                    <span class="think-toggle-btn" id="btn-${thinkId}">▶</span>
                </div>
                <div class="think-collapsible-content" id="${thinkId}" style="display: none;">
                    ${escapeHtml(content.trim())}
                </div>
            </div>
        `;
    });
    
    return processedText;
}

// 只提取思考过程部分
function processThinkTagsOnly(text) {
    if (!text) return '';
    
    // 使用正则表达式匹配<think>标签
    const thinkRegex = /<think>([\s\S]*?)<\/think>/g;
    let thinkContent = '';
    let thinkIndex = 0;
    let match;
    
    while ((match = thinkRegex.exec(text)) !== null) {
        thinkIndex++;
        const thinkId = `think-${Date.now()}-${thinkIndex}`;
        thinkContent += `
            <div class="think-collapsible-section">
                <div class="think-collapsible-header" onclick="toggleThinkCollapse('${thinkId}')">
                    <span>🤔 思考过程</span>
                    <span class="think-toggle-btn" id="btn-${thinkId}">▶</span>
                </div>
                <div class="think-collapsible-content" id="${thinkId}" style="display: none;">
                    ${escapeHtml(match[1].trim())}
                </div>
            </div>
        `;
    }
    
    return thinkContent;
}

// 渲染Markdown内容，移除思考过程标签
function renderMarkdown(text) {
    if (!text) return '';
    
    // 移除<think>标签及其内容
    const thinkRegex = /<think>[\s\S]*?<\/think>/g;
    let cleanText = text.replace(thinkRegex, '').trim();
    
    // 使用marked.js渲染Markdown
    if (typeof marked !== 'undefined') {
        // 配置marked选项
        marked.setOptions({
            breaks: true, // 支持换行符转换为<br>
            gfm: true, // 启用GitHub风格Markdown
            sanitize: false, // 允许HTML标签（用于更好的格式化）
            smartLists: true, // 智能列表
            smartypants: true // 智能标点符号
        });
        
        try {
            return marked.parse(cleanText);
        } catch (error) {
            console.error('Markdown渲染失败:', error);
            // 如果渲染失败，回退到HTML转义
            return escapeHtml(cleanText).replace(/\n/g, '<br>');
        }
    } else {
        // 如果marked.js未加载，回退到HTML转义
        console.warn('marked.js未加载，使用纯文本显示');
        return escapeHtml(cleanText).replace(/\n/g, '<br>');
    }
}

// 保留原函数名以保持兼容性
function removeThinkTags(text) {
    return renderMarkdown(text);
}

// 切换<think>标签折叠状态
function toggleThinkCollapse(thinkId) {
    const content = document.getElementById(thinkId);
    const button = document.getElementById(`btn-${thinkId}`);
    
    if (content && button) {
        const isCollapsed = content.style.display === 'none';
        content.style.display = isCollapsed ? 'block' : 'none';
        button.textContent = isCollapsed ? '▼' : '▶';
    }
}

// 测试Markdown渲染功能
function testMarkdownRendering() {
    const testMarkdown = `# 测试标题

这是一个**粗体文本**和*斜体文本*的示例。

## 二级标题

- 列表项1
- 列表项2
  - 嵌套列表项
  - 另一个嵌套项

### 代码示例

\`\`\`javascript
function hello() {
    console.log("Hello, World!");
}
\`\`\`

行内代码：\`console.log()\`

> 这是一个引用块

| 列1 | 列2 | 列3 |
|-----|-----|-----|
| 数据1 | 数据2 | 数据3 |
| 数据4 | 数据5 | 数据6 |

<think>这是思考过程</think>

这是最终的答案内容。`;

    const rendered = renderMarkdown(testMarkdown);
    console.log('Markdown渲染测试结果:', rendered);
    return rendered;
}
