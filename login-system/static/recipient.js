let currentView = 'available';

// Load available projects on page load
document.addEventListener('DOMContentLoaded', function() {
    loadAvailableProjects();
    setupEventListeners();
    
    // ### 新增: 綁定評價表單提交事件 ###
    const reviewForm = document.getElementById('reviewForm');
    if(reviewForm) reviewForm.addEventListener('submit', submitReview);
});

function setupEventListeners() {
    document.getElementById('availableTab').addEventListener('click', function(e) {
        e.preventDefault();
        currentView = 'available';
        loadAvailableProjects();
    });
    
    document.getElementById('myProjectsTab').addEventListener('click', function(e) {
        e.preventDefault();
        currentView = 'myprojects';
        loadMyProjects();
    });
    
    document.getElementById('historyTab').addEventListener('click', function(e) {
        e.preventDefault();
        currentView = 'history';
        loadHistory();
    });
    
    document.getElementById('quoteForm').addEventListener('submit', submitQuote);
    document.getElementById('messageForm').addEventListener('submit', sendMessage);
    document.getElementById('uploadForm').addEventListener('submit', uploadClosureFile);
}

async function loadAvailableProjects() {
    try {
        const response = await fetch('/api/available_projects');
        const projects = await response.json();
        
        const container = document.getElementById('availableProjectsList');
        container.innerHTML = '';
        
        if (projects.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>目前沒有可用項目。</p></div>';
            return;
        }
        
        projects.forEach(project => {
            const card = createAvailableProjectCard(project);
            container.appendChild(card);
        });
    } catch (error) {
        console.error('Error loading available projects:', error);
    }
}

function createAvailableProjectCard(project) {
    const card = document.createElement('div');
    card.className = 'project-card';
    
    // ### 修正重點：處理單引號轉義，防止 JS 崩潰 ###
    // 原本這裡用的是舊代碼，現在已修正
    const reviewsData = JSON.stringify(project.delegator_rating.reviews).replace(/'/g, "&#39;");
    const ratingHtml = `<span style="cursor:pointer; color:#f39c12; font-size:0.9em; margin-left:8px;" onclick='showUserReviews(${reviewsData}, ${project.delegator_rating.count}, ${project.delegator_rating.average})'>★ ${project.delegator_rating.average} (${project.delegator_rating.count})</span>`;
    
    card.innerHTML = `
        <h3>${project.title}</h3>
        <p>${project.description}</p>
        <p><strong>委託方：</strong> ${project.delegator_name} ${ratingHtml}</p>
        <p><strong>目前報價數：</strong> ${project.quote_count ?? 0}</p>
        ${project.deadline ? `<p><strong>提案截止期限：</strong> ${new Date(project.deadline).toLocaleString()}</p>` : ''}
        <p><strong>發布時間：</strong> ${new Date(project.created_at).toLocaleDateString()}</p>
        <div class="project-actions">
            ${!project.has_quoted ? `
                <button class="btn btn-primary" onclick="showQuoteModal(${project.id})">提交報價</button>
            ` : `
                <button class="btn btn-secondary" disabled>已提交報價</button>
            `}
        </div>
    `;
    
    return card;
}

async function loadMyProjects() {
    try {
        const response = await fetch('/api/my_projects');
        const projects = await response.json();
        
        const container = document.getElementById('dashboardContent');
        
        if (projects.length === 0) {
            container.innerHTML = '<div class="dashboard-section"><h2>我的活躍項目</h2><div class="empty-state"><p>您還沒有任何活躍項目。</p></div></div>';
            return;
        }
        
        let html = '<div class="dashboard-section"><h2>我的活躍項目</h2><div id="myProjectsList">';
        
        projects.forEach(project => {
            const card = createMyProjectCard(project);
            html += card.outerHTML;
        });
        
        html += '</div></div>';
        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading my projects:', error);
    }
}

function createMyProjectCard(project) {
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
        reviewBtn = `<button class="btn btn-warning" onclick="openDelegatorReview(${project.id})">評價委託方</button>`;
    }
    
    card.innerHTML = `
        <h3>${project.title} <span class="status-badge ${statusClass}">${statusText[project.status] || project.status}</span></h3>
        <p>${project.description}</p>
        <p><strong>委託方：</strong> ${project.delegator_name}</p>
        <p><strong>開始時間：</strong> ${new Date(project.created_at).toLocaleDateString()}</p>
        <div class="project-actions">
            <button class="btn btn-primary" onclick="viewMessages(${project.id}, '${project.title}')">訊息</button>
            ${project.status === 'active' ? `
                <button class="btn btn-success" onclick="showUploadModal(${project.id})">上傳結案文件</button>
            ` : ''}
            ${reviewBtn}
        </div>
    `;
    
    return card;
}

function showQuoteModal(projectId) {
    document.getElementById('quoteProjectId').value = projectId;
    document.getElementById('quoteForm').reset();
    document.getElementById('quoteModal').style.display = 'block';
}

async function submitQuote(e) {
    e.preventDefault();
    
    const projectId = document.getElementById('quoteProjectId').value;
    const amount = document.getElementById('quoteAmount').value;
    const message = document.getElementById('quoteMessage').value;
    const proposalFile = document.getElementById('proposalFile').files[0];
    
    if (!proposalFile) {
        alert('請上傳提案計畫書（PDF格式）');
        return;
    }
    
    if (!proposalFile.name.toLowerCase().endsWith('.pdf')) {
        alert('提案計畫書必須是PDF格式');
        return;
    }
    
    try {
        // 先提交報價
        const quoteResponse = await fetch(`/api/projects/${projectId}/quote`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ amount: parseFloat(amount), message })
        });
        
        const quoteData = await quoteResponse.json();
        
        if (!quoteData.success) {
            alert(quoteData.error || '提交報價時出錯');
            return;
        }
        
        // 上傳提案文件
        const formData = new FormData();
        formData.append('file', proposalFile);
        
        const fileResponse = await fetch(`/api/quotes/${quoteData.quote_id}/upload_proposal`, {
            method: 'POST',
            body: formData
        });
        
        const fileData = await fileResponse.json();
        
        if (fileData.success) {
            closeQuoteModal();
            loadAvailableProjects();
            alert('報價和提案計畫書提交成功！');
        } else {
            alert(fileData.error || '上傳提案計畫書時出錯');
        }
    } catch (error) {
        alert('提交報價時出錯');
        console.error(error);
    }
}

async function viewMessages(projectId, projectTitle) {
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

async function showUploadModal(projectId) {
    document.getElementById('uploadProjectId').value = projectId;
    document.getElementById('uploadForm').reset();
    
    // 載入文件歷史
    await loadClosureFilesHistory(projectId);
    
    document.getElementById('uploadModal').style.display = 'block';
}

async function loadClosureFilesHistory(projectId) {
    try {
        const response = await fetch(`/api/projects/${projectId}/closure_files`);
        const files = await response.json();
        
        const container = document.getElementById('closureFilesHistory');
        container.innerHTML = '';
        
        if (files.length > 0) {
            container.innerHTML = '<h3>已上傳的版本：</h3>';
            files.forEach(file => {
                const fileDiv = document.createElement('div');
                fileDiv.className = 'quote-card';
                const statusText = {
                    'pending': '待審核',
                    'accepted': '已接受',
                    'returned': '已退回'
                };
                fileDiv.innerHTML = `
                    <p><strong>版本 ${file.version}:</strong> ${file.original_filename}</p>
                    <p><strong>狀態：</strong> <span class="status-badge status-${file.status}">${statusText[file.status] || file.status}</span></p>
                    <p><strong>上傳時間：</strong> ${new Date(file.created_at).toLocaleString()}</p>
                    <a href="/api/files/${file.id}/download?file_type=closure" target="_blank" class="btn btn-sm btn-link">下載</a>
                `;
                container.appendChild(fileDiv);
            });
        }
    } catch (error) {
        console.error('載入文件歷史時出錯:', error);
    }
}

async function uploadClosureFile(e) {
    e.preventDefault();
    
    const projectId = document.getElementById('uploadProjectId').value;
    const fileInput = document.getElementById('closureFile');
    
    if (!fileInput.files.length) {
        alert('請選擇一個文件');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    
    try {
        const response = await fetch(`/api/projects/${projectId}/upload_closure`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(`文件上傳成功！版本 ${data.version}`);
            await loadClosureFilesHistory(projectId);
            document.getElementById('uploadForm').reset();
        } else {
            alert(data.error || '上傳文件時出錯');
        }
    } catch (error) {
        alert('上傳文件時出錯');
        console.error(error);
    }
}

async function loadHistory() {
    try {
        const response = await fetch('/api/history');
        const projects = await response.json();
        
        const container = document.getElementById('dashboardContent');
        
        if (projects.length === 0) {
            container.innerHTML = '<div class="dashboard-section"><h2>項目歷史</h2><div class="empty-state"><p>還沒有完成的項目。</p></div></div>';
            return;
        }
        
        let html = '<div class="dashboard-section"><h2>項目歷史</h2><div id="historyList">';
        
        projects.forEach(project => {
            const card = createMyProjectCard(project);
            html += card.outerHTML;
        });
        
        html += '</div></div>';
        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading history:', error);
    }
}

function closeQuoteModal() {
    document.getElementById('quoteModal').style.display = 'none';
}

function closeMessagesModal() {
    document.getElementById('messagesModal').style.display = 'none';
}

function closeUploadModal() {
    document.getElementById('uploadModal').style.display = 'none';
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

// 打開評價委託方視窗 (乙方用)
function openDelegatorReview(projectId) {
    document.getElementById('reviewProjectId').value = projectId;
    // 設置乙方評甲方的三個維度
    document.getElementById('labelDim1').textContent = '需求合理性';
    document.getElementById('labelDim2').textContent = '驗收難度';
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
            else loadMyProjects();
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