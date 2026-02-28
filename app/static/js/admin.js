const API_BASE = '';
let allUsers = [];
let userToDelete = null;
let userToEdit = null;

document.addEventListener('DOMContentLoaded', function() {
    loadUsers();
    attachEventListeners();
});

function attachEventListeners() {
    document.getElementById('refresh-btn').addEventListener('click', loadUsers);
    document.getElementById('search-box').addEventListener('input', filterTable);
    document.getElementById('status-filter').addEventListener('change', filterTable);
    document.getElementById('confirm-delete-btn').addEventListener('click', deleteUser);
    document.getElementById('edit-form').addEventListener('submit', saveUserChanges);
    
    document.getElementById('logout-btn').addEventListener('click', async function() {
        await fetch(`${API_BASE}/api/logout`, { method: 'POST' });
        window.location.href = '/';
    });
}

async function loadUsers() {
    try {
        const response = await fetch(`${API_BASE}/api/admin/users?page=1&per_page=100`);
        
        if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
                window.location.href = '/login';
            }
            throw new Error('Failed to load users');
        }
        
        const data = await response.json();
        allUsers = data.users || [];
        
        renderTable(allUsers);
        document.getElementById('total-count').textContent = allUsers.length;
    } catch (error) {
        console.error('Error loading users:', error);
        document.getElementById('table-body').innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; padding: 2rem; color: red;">
                    Error loading users: ${error.message}
                </td>
            </tr>
        `;
    }
}

function renderTable(users) {
    const tableBody = document.getElementById('table-body');
    
    if (users.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; padding: 2rem; color: var(--text-color);">
                    No users found
                </td>
            </tr>
        `;
        return;
    }
    
    tableBody.innerHTML = users.map((user, index) => `
        <tr style="border-bottom: 1px solid var(--border-color); ${index % 2 === 0 ? 'background: #f9f9f9;' : ''}">
            <td style="padding: 1rem; border-right: 1px solid var(--border-color);">${user.user_id}</td>
            <td style="padding: 1rem; border-right: 1px solid var(--border-color);">${user.name}</td>
            <td style="padding: 1rem; border-right: 1px solid var(--border-color);">${user.email}</td>
            <td style="padding: 1rem; border-right: 1px solid var(--border-color);">${user.phone}</td>
            <td style="padding: 1rem; border-right: 1px solid var(--border-color);">
                <span style="background: ${user.role === 'admin' ? 'var(--primary-color)' : 'var(--secondary-color)'}; color: white; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.85rem;">
                    ${user.role}
                </span>
            </td>
            <td style="padding: 1rem; border-right: 1px solid var(--border-color);">
                <span style="background: ${user.is_verified ? '#e6f7f0' : '#ffe6f0'}; color: ${user.is_verified ? '#2d7a63' : '#d63384'}; padding: 0.25rem 0.75rem; border-radius: 4px; font-size: 0.85rem;">
                    ${user.is_verified ? 'Verified' : 'Unverified'}
                </span>
            </td>
            <td style="padding: 1rem; border-right: 1px solid var(--border-color);">
                ${new Date(user.created_at).toLocaleDateString()}
            </td>
            <td style="padding: 1rem; text-align: center;">
                <button class="btn" style="padding: 0.5rem 0.8rem; font-size: 0.9rem; background: var(--primary-color); color: white; border: none; border-radius: 4px; cursor: pointer; margin-right: 0.25rem;" onclick="openEditModal(${user.user_id})">Edit</button>
                <button class="btn" style="padding: 0.5rem 0.8rem; font-size: 0.9rem; background: var(--danger-color); color: white; border: none; border-radius: 4px; cursor: pointer;" onclick="openDeleteModal(${user.user_id}, '${user.name}')">Delete</button>
            </td>
        </tr>
    `).join('');
}

function filterTable() {
    const searchTerm = document.getElementById('search-box').value.toLowerCase();
    const statusFilter = document.getElementById('status-filter').value;
    
    let filtered = allUsers.filter(user => {
        const matchesSearch = user.name.toLowerCase().includes(searchTerm) || 
                            user.email.toLowerCase().includes(searchTerm) ||
                            user.phone.includes(searchTerm);
        
        const matchesStatus = !statusFilter || 
                            (statusFilter === 'verified' && user.is_verified) ||
                            (statusFilter === 'unverified' && !user.is_verified);
        
        return matchesSearch && matchesStatus;
    });
    
    renderTable(filtered);
}

function openDeleteModal(userId, userName) {
    userToDelete = userId;
    document.getElementById('delete-message').textContent = 
        `Are you sure you want to delete "${userName}"? This action cannot be undone.`;
    document.getElementById('delete-modal').style.display = 'block';
}

async function deleteUser() {
    if (!userToDelete) return;
    
    try {
        const response = await fetch(`${API_BASE}/api/admin/users/${userToDelete}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            alert('User deleted successfully');
            document.getElementById('delete-modal').style.display = 'none';
            loadUsers();
        } else {
            alert('Error deleting user');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error deleting user: ' + error.message);
    }
}

function openEditModal(userId) {
    const user = allUsers.find(u => u.user_id === userId);
    if (!user) return;
    
    userToEdit = userId;
    document.getElementById('edit-name').value = user.name;
    document.getElementById('edit-email').value = user.email;
    document.getElementById('edit-status').value = user.is_verified ? 'verified' : 'unverified';
    document.getElementById('edit-modal').style.display = 'block';
}

async function saveUserChanges(e) {
    e.preventDefault();
    
    if (!userToEdit) return;
    
    try {
        const isVerified = document.getElementById('edit-status').value === 'verified';
        const response = await fetch(`${API_BASE}/api/admin/users/${userToEdit}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: document.getElementById('edit-name').value,
                email: document.getElementById('edit-email').value,
                is_verified: isVerified
            })
        });
        
        if (response.ok) {
            alert('User updated successfully');
            document.getElementById('edit-modal').style.display = 'none';
            loadUsers();
        } else {
            const error = await response.json();
            alert('Error: ' + (error.error || 'Failed to update user'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error updating user: ' + error.message);
    }
}