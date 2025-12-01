let currentView = 'available';

// Load available projects on page load
document.addEventListener('DOMContentLoaded', function() {
    loadAvailableProjects();
    setupEventListeners();
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
    
    card.innerHTML = `
        <h3>${project.title}</h3>
        <p>${project.description}</p>
        <p><strong>委託方：</strong> ${project.delegator_name}</p>
        <p><strong>目前報價數：</strong> ${project.quote_count ?? 0}</p>
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
    
    try {
        const response = await fetch(`/api/projects/${projectId}/quote`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ amount: parseFloat(amount), message })
        });
        
        const data = await response.json();
        
        if (data.success) {
            closeQuoteModal();
            loadAvailableProjects();
            alert('報價提交成功！');
        } else {
            alert(data.error || '提交報價時出錯');
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

function showUploadModal(projectId) {
    document.getElementById('uploadProjectId').value = projectId;
    document.getElementById('uploadForm').reset();
    document.getElementById('uploadModal').style.display = 'block';
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
            closeUploadModal();
            loadMyProjects();
            alert('文件上傳成功！');
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

// Close modals when clicking outside
window.onclick = function(event) {
    const modals = document.getElementsByClassName('modal');
    for (let modal of modals) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    }
}

