let currentProjectId = null;
let currentView = 'projects';

// Load projects on page load
document.addEventListener('DOMContentLoaded', function() {
    loadProjects();
    setupEventListeners();
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
    
    card.innerHTML = `
        <h3>${project.title} <span class="status-badge ${statusClass}">${statusText[project.status] || project.status}</span></h3>
        <p>${project.description}</p>
        <p><strong>創建時間：</strong> ${new Date(project.created_at).toLocaleDateString()}</p>
        ${project.delegate_name ? `<p><strong>受託人：</strong> ${project.delegate_name}</p>` : ''}
        ${project.status === 'pending' ? `<p><strong>報價數：</strong> ${project.quote_count}</p>` : ''}
        <div class="project-actions">
            ${project.status === 'pending' ? `
                <button class="btn btn-primary" onclick="editProject(${project.id})">編輯</button>
                <button class="btn btn-success" onclick="viewQuotes(${project.id})">查看報價 (${project.quote_count})</button>
                <button class="btn btn-danger" onclick="deleteProject(${project.id})">刪除</button>
            ` : ''}
            ${project.status === 'active' ? `
                <button class="btn btn-primary" onclick="viewMessages(${project.id}, '${project.title}')">訊息</button>
                <button class="btn btn-success" onclick="closeProject(${project.id})">結案項目</button>
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
    
    const url = projectId ? `/api/projects/${projectId}` : '/api/projects';
    const method = projectId ? 'PUT' : 'POST';
    
    try {
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ title, description })
        });
        
        const data = await response.json();
        
        if (data.success) {
            closeProjectModal();
            loadProjects();
        } else {
            alert(data.error || '保存項目時出錯');
        }
    } catch (error) {
        alert('保存項目時出錯');
        console.error(error);
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
                quoteCard.innerHTML = `
                    <h4>來自：${quote.recipient_name}</h4>
                    <p><strong>金額：</strong> ${quote.amount.toFixed(2)} 元</p>
                    ${quote.message ? `<p>${quote.message}</p>` : ''}
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

// Close modals when clicking outside
window.onclick = function(event) {
    const modals = document.getElementsByClassName('modal');
    for (let modal of modals) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    }
}

