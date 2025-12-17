let currentProjectId = null;
let currentView = 'projects';

// Load projects on page load
document.addEventListener('DOMContentLoaded', function() {
    loadProjects();
    setupEventListeners();
    
    // ### 新增: 綁定評價表單提交事件 ###
    const reviewForm = document.getElementById('reviewForm');
    if(reviewForm) reviewForm.addEventListener('submit', submitReview);
});

function setupEventListeners() {
    document.getElementById('projectsTab').addEventListener('click', function(e) {
        e.preventDefault();
        currentView = 'projects';
        loadProjects();
    });
    
    document.getElementById('historyTab').addEventListener('click', function(e) {
        e.preventDefault();
        currentView = 'history';
        loadHistory();
    });
    
    document.getElementById('projectForm').addEventListener('submit', saveProject);
    document.getElementById('messageForm').addEventListener('submit', sendMessage);
}

async function loadProjects() {
    try {
        const response = await fetch('/api/projects');
        const projects = await response.json();
        
        const container = document.getElementById('projectsList');
        container.innerHTML = '';
        
        if (projects.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>還沒有項目。創建您的第一個項目吧！</p></div>';
            return;
        }
        
        projects.forEach(project => {
            const card = createProjectCard(project);
            container.appendChild(card);
        });
    } catch (error) {
        console.error('Error loading projects:', error);
    }
}

function createProjectCard(project) {
    const card = document.createElement('div');
    card.className = 'project-card';
    
    const statusClass = `status-${project.status}`;
    
    const statusText = {
        'pending': '待處理',
        'active': '進行中',
        'completed': '已完成',
        'closed': '已結案'
    };
    
    // ### 新增: 判斷是否顯示評價按鈕 ###
    let reviewBtn = '';
    if (project.status === 'closed') {
        reviewBtn = `<button class="btn btn-warning" onclick="openRecipientReview(${project.id})">評價受託方</button>`;
    }
    
    card.innerHTML = `
        <h3>${project.title} <span class="status-badge ${statusClass}">${statusText[project.status] || project.status}</span></h3>
        <p>${project.description}</p>
        <p><strong>創建時間：</strong> ${new Date(project.created_at).toLocaleDateString()}</p>
        ${project.deadline ? `<p><strong>提案截止期限：</strong> ${new Date(project.deadline).toLocaleString()}</p>` : ''}
        ${project.delegate_name ? `<p><strong>受託人：</strong> ${project.delegate_name}</p>` : ''}
        ${project.status === 'pending' ? `<p><strong>報價數：</strong> ${project.quote_count}</p>` : ''}
        <div class="project-actions">
            ${project.status === 'pending' ? `
                <button class="btn btn-primary" onclick="editProject(${project.id})">編輯</button>
                <button class="btn btn-success" onclick="viewQuotes(${project.id})">查看報價 (${project.quote_count})</button>
                <button class="btn btn-danger" onclick="deleteProject(${project.id})">刪除</button>
            ` : ''}
            ${project.status === 'active' || project.status === 'closed' ? `
                <button class="btn btn-primary" onclick="viewMessages(${project.id}, '${project.title}')">訊息</button>
                <button class="btn btn-info" onclick="viewClosureFiles(${project.id})">查看結案文件</button>
                ${project.status === 'active' ? `
                    <button class="btn btn-success" onclick="closeProject(${project.id})">結案項目</button>
                ` : ''}
                ${reviewBtn}
            ` : ''}
        </div>
    `;
    
    return card;
}

function showCreateProject() {
    document.getElementById('modalTitle').textContent = '創建新項目';
    document.getElementById('projectForm').reset();
    document.getElementById('projectId').value = '';
    document.getElementById('projectModal').style.display = 'block';
}

function editProject(projectId) {
    fetch(`/api/projects/${projectId}`)
        .then(res => res.json())
        .then(project => {
            document.getElementById('modalTitle').textContent = '編輯項目';
            document.getElementById('projectId').value = project.id;
            document.getElementById('projectTitle').value = project.title;
            document.getElementById('projectDescription').value = project.description;
            
            // 設置截止日期
            if (project.deadline) {
                const deadlineDate = new Date(project.deadline);
                const localDateTime = new Date(deadlineDate.getTime() - deadlineDate.getTimezoneOffset() * 60000);
                document.getElementById('projectDeadline').value = localDateTime.toISOString().slice(0, 16);
            } else {
                document.getElementById('projectDeadline').value = '';
            }
            
            document.getElementById('projectModal').style.display = 'block';
        })
        .catch(err => {
            alert('載入項目時出錯');
            console.error(err);
        });
}

async function saveProject(e) {
    e.preventDefault();
    
    const projectId = document.getElementById('projectId').value;
    const title = document.getElementById('projectTitle').value;
    const description = document.getElementById('projectDescription').value;
    const deadline = document.getElementById('projectDeadline').value;
    
    const url = projectId ? `/api/projects/${projectId}` : '/api/projects';
    const method = projectId ? 'PUT' : 'POST';
    
    const body = { title, description };
    if (deadline) {
        // 將本地時間轉換為ISO格式
        const deadlineDate = new Date(deadline);
        body.deadline = deadlineDate.toISOString();
    } else if (projectId) {
        body.deadline = null;
    }
    
    try {
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(body)
        });
        
        const data = await response.json();
        
        if (data.success) {
            closeProjectModal();
            loadProjects();
        } else {
            alert(data.error || data.detail || '保存項目時出錯');
        }
    } catch (error) {
        console.error('保存項目錯誤:', error);
        // 嘗試解析錯誤響應
        try {
            const errorData = await error.response?.json();
            alert(errorData?.error || errorData?.detail || '保存項目時出錯');
        } catch {
            alert('保存項目時出錯：' + error.message);
        }
    }
}

async function deleteProject(projectId) {
    if (!confirm('您確定要刪除此項目嗎？')) return;
    
    try {
        const response = await fetch(`/api/projects/${projectId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            loadProjects();
        } else {
            alert(data.error || '刪除項目時出錯');
        }
    } catch (error) {
        alert('刪除項目時出錯');
        console.error(error);
    }
}

async function viewQuotes(projectId) {
    try {
        const response = await fetch(`/api/projects/${projectId}/quotes`);
        const quotes = await response.json();
        
        const container = document.getElementById('quotesList');
        container.innerHTML = '';
        
        if (quotes.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>此項目還沒有報價。</p></div>';
        } else {
            quotes.forEach(quote => {
                const quoteCard = document.createElement('div');
                quoteCard.className = 'quote-card';
                
                // ### 修正重點：處理單引號轉義，防止 JS 崩潰 ###
                const reviewsData = JSON.stringify(quote.recipient_rating.reviews).replace(/'/g, "&#39;");
                const ratingHtml = `<span style="cursor:pointer; color:#f39c12; font-size:0.9em; margin-left:8px;" onclick='showUserReviews(${reviewsData}, ${quote.recipient_rating.count}, ${quote.recipient_rating.average})'>★ ${quote.recipient_rating.average} (${quote.recipient_rating.count})</span>`;
                
                quoteCard.innerHTML = `
                    <h4>來自：${quote.recipient_name} ${ratingHtml}</h4>
                    <p><strong>金額：</strong> ${quote.amount.toFixed(2)} 元</p>
                    ${quote.message ? `<p>${quote.message}</p>` : ''}
                    ${quote.proposal_file ? `
                        <p><strong>提案計畫書：</strong> 
                            <a href="/api/files/${quote.proposal_file.id}/download?file_type=proposal" target="_blank" class="btn btn-sm btn-link">
                                ${quote.proposal_file.original_filename}
                            </a>
                        </p>
                    ` : '<p><strong>提案計畫書：</strong> 未上傳</p>'}
                    <p><strong>狀態：</strong> <span class="status-badge status-${quote.status}">${quote.status === 'pending' ? '待處理' : quote.status === 'accepted' ? '已接受' : '已拒絕'}</span></p>
                    <p><small>提交時間：${new Date(quote.created_at).toLocaleString()}</small></p>
                    ${quote.status === 'pending' ? `
                        <button class="btn btn-success" onclick="selectDelegate(${projectId}, ${quote.id})">選擇此受託人</button>
                    ` : ''}
                `;
                container.appendChild(quoteCard);
            });
        }
        
        document.getElementById('quotesModal').style.display = 'block';
    } catch (error) {
        alert('載入報價時出錯');
        console.error(error);
    }
}

async function selectDelegate(projectId, quoteId) {
    if (!confirm('您確定要選擇此受託人嗎？')) return;
    
    try {
        const response = await fetch(`/api/projects/${projectId}/select_delegate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ quote_id: quoteId })
        });
        
        const data = await response.json();
        
        if (data.success) {
            closeQuotesModal();
            loadProjects();
            alert('受託人選擇成功！');
        } else {
            alert(data.error || '選擇受託人時出錯');
        }
    } catch (error) {
        alert('選擇受託人時出錯');
        console.error(error);
    }
}

async function viewMessages(projectId, projectTitle) {
    currentProjectId = projectId;
    document.getElementById('messagesTitle').textContent = `訊息 - ${projectTitle}`;
    document.getElementById('messageProjectId').value = projectId;
    
    await loadMessages(projectId);
    document.getElementById('messagesModal').style.display = 'block';
}

async function loadMessages(projectId) {
    try {
        const response = await fetch(`/api/projects/${projectId}/messages`);
        const messages = await response.json();
        
        const container = document.getElementById('messagesContainer');
        container.innerHTML = '';
        
        if (messages.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>還沒有訊息。開始對話吧！</p></div>';
        } else {
            messages.forEach(message => {
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message-item';
                messageDiv.innerHTML = `
                    <div class="message-header">
                        ${message.sender_name}
                        <span class="message-time">${new Date(message.created_at).toLocaleString()}</span>
                    </div>
                    <div class="message-body">${message.content}</div>
                `;
                container.appendChild(messageDiv);
            });
        }
        
        container.scrollTop = container.scrollHeight;
    } catch (error) {
        console.error('Error loading messages:', error);
    }
}

async function sendMessage(e) {
    e.preventDefault();
    
    const projectId = document.getElementById('messageProjectId').value;
    const content = document.getElementById('messageContent').value;
    
    try {
        const response = await fetch(`/api/projects/${projectId}/messages`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ content })
        });
        
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('messageContent').value = '';
            await loadMessages(projectId);
        } else {
            alert(data.error || '發送訊息時出錯');
        }
    } catch (error) {
        alert('發送訊息時出錯');
        console.error(error);
    }
}

async function closeProject(projectId) {
    if (!confirm('您要結案並接受此項目嗎？')) return;
    
    try {
        const response = await fetch(`/api/projects/${projectId}/close`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ action: 'accept' })
        });
        
        const data = await response.json();
        
        if (data.success) {
            loadProjects();
            alert('項目結案成功！');
        } else {
            alert(data.error || '結案項目時出錯');
        }
    } catch (error) {
        alert('結案項目時出錯');
        console.error(error);
    }
}

async function loadHistory() {
    try {
        const response = await fetch('/api/history');
        const projects = await response.json();
        
        const container = document.getElementById('projectsList');
        container.innerHTML = '<h2>項目歷史</h2>';
        
        if (projects.length === 0) {
            container.innerHTML += '<div class="empty-state"><p>還沒有完成的項目。</p></div>';
            return;
        }
        
        projects.forEach(project => {
            const card = createProjectCard(project);
            container.appendChild(card);
        });
    } catch (error) {
        console.error('Error loading history:', error);
    }
}

function closeProjectModal() {
    document.getElementById('projectModal').style.display = 'none';
}

function closeQuotesModal() {
    document.getElementById('quotesModal').style.display = 'none';
}

function closeMessagesModal() {
    document.getElementById('messagesModal').style.display = 'none';
}

async function viewClosureFiles(projectId) {
    try {
        const response = await fetch(`/api/projects/${projectId}/closure_files`);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: '未知錯誤' }));
            throw new Error(errorData.error || errorData.detail || `HTTP ${response.status}`);
        }
        
        const files = await response.json();
        
        const container = document.getElementById('closureFilesList');
        if (!container) {
            console.error('找不到 closureFilesList 元素');
            return;
        }
        
        container.innerHTML = '';
        
        if (!files || files.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>還沒有上傳結案文件。</p></div>';
        } else {
            files.forEach(file => {
                const fileCard = document.createElement('div');
                fileCard.className = 'quote-card';
                const statusText = {
                    'pending': '待審核',
                    'accepted': '已接受',
                    'returned': '已退回'
                };
                fileCard.innerHTML = `
                    <h4>版本 ${file.version || 1} - ${file.original_filename || file.filename || '未知文件'}</h4>
                    <p><strong>上傳者：</strong> ${file.uploader_name || '未知'}</p>
                    <p><strong>狀態：</strong> <span class="status-badge status-${file.status || 'pending'}">${statusText[file.status] || file.status || '未知'}</span></p>
                    <p><strong>上傳時間：</strong> ${file.created_at ? new Date(file.created_at).toLocaleString() : '未知'}</p>
                    <div class="project-actions">
                        <a href="/api/files/${file.id}/download?file_type=closure" target="_blank" class="btn btn-primary">下載</a>
                        ${file.status === 'pending' ? `
                            <button class="btn btn-success" onclick="acceptClosureFile(${projectId}, ${file.id})">接受</button>
                            <button class="btn btn-warning" onclick="returnClosureFile(${projectId}, ${file.id})">退回</button>
                        ` : ''}
                    </div>
                `;
                container.appendChild(fileCard);
            });
        }
        
        const modal = document.getElementById('closureFilesModal');
        if (modal) {
            modal.style.display = 'block';
        } else {
            console.error('找不到 closureFilesModal 元素');
        }
    } catch (error) {
        console.error('載入結案文件錯誤:', error);
        alert('載入結案文件時出錯: ' + error.message);
    }
}

async function acceptClosureFile(projectId, fileId) {
    if (!confirm('確定要接受此版本的文件嗎？')) return;
    
    try {
        const response = await fetch(`/api/projects/${projectId}/close`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ action: 'accept', file_id: fileId })
        });
        
        const data = await response.json();
        
        if (data.success) {
            viewClosureFiles(projectId);
            loadProjects();
        } else {
            alert(data.error || '接受文件時出錯');
        }
    } catch (error) {
        alert('接受文件時出錯');
        console.error(error);
    }
}

async function returnClosureFile(projectId, fileId) {
    if (!confirm('確定要退回此版本的文件嗎？受託方可以上傳新版本。')) return;
    
    try {
        const response = await fetch(`/api/projects/${projectId}/close`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ action: 'return', file_id: fileId })
        });
        
        const data = await response.json();
        
        if (data.success) {
            viewClosureFiles(projectId);
            loadProjects();
        } else {
            alert(data.error || '退回文件時出錯');
        }
    } catch (error) {
        alert('退回文件時出錯');
        console.error(error);
    }
}

function closeClosureFilesModal() {
    document.getElementById('closureFilesModal').style.display = 'none';
}

// ### 新增功能：評價系統相關邏輯 ###

// 顯示評價歷史 (共用)
function showUserReviews(reviews, count, avg) {
    const container = document.getElementById('reviewsHistoryList');
    container.innerHTML = `
        <div class="review-summary">
            <h3>總評分: ${avg} ⭐ (${count} 次評價)</h3>
        </div>
        <hr>
    `;
    
    if (reviews.length === 0) {
        container.innerHTML += '<p>尚無詳細評論。</p>';
    } else {
        reviews.forEach(r => {
            container.innerHTML += `
                <div class="review-item" style="margin-bottom:15px; border-bottom:1px solid #eee; padding-bottom:10px;">
                    <div><strong>評分:</strong> ${r.average} ⭐</div>
                    <p>${r.comment}</p>
                    <small style="color:#888;">${new Date(r.created_at).toLocaleDateString()}</small>
                </div>
            `;
        });
    }
    document.getElementById('viewReviewsModal').style.display = 'block';
}

// 關閉評價視窗
function closeReviewModal() {
    document.getElementById('reviewModal').style.display = 'none';
}

// 打開評價受託方視窗 (甲方用)
function openRecipientReview(projectId) {
    document.getElementById('reviewProjectId').value = projectId;
    // 設置甲方評乙方的三個維度
    document.getElementById('labelDim1').textContent = '產出品質';
    document.getElementById('labelDim2').textContent = '執行效率';
    document.getElementById('labelDim3').textContent = '合作態度';
    document.getElementById('reviewModal').style.display = 'block';
}

// 處理提交評價
async function submitReview(e) {
    e.preventDefault();
    const projectId = document.getElementById('reviewProjectId').value;
    
    const body = {
        dimension_1: document.getElementById('dim1').value,
        dimension_2: document.getElementById('dim2').value,
        dimension_3: document.getElementById('dim3').value,
        comment: document.getElementById('reviewComment').value
    };
    
    try {
        const response = await fetch(`/api/projects/${projectId}/review`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body)
        });
        const data = await response.json();
        if(data.success) {
            alert('評價提交成功！');
            closeReviewModal();
            // 重新載入以更新按鈕狀態
            if(currentView === 'history') loadHistory(); 
            else loadProjects();
        } else {
            alert(data.error || '提交失敗，您可能已經評價過此項目。');
        }
    } catch(err) {
        alert('發生錯誤');
        console.error(err);
    }
}

// Close modals when clicking outside
window.onclick = function(event) {
    const modals = document.getElementsByClassName('modal');
    for (let modal of modals) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    }
}