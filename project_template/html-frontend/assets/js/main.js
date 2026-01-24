/**
 * 主脚本文件
 */

// DOM加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    console.log('页面加载完成');
    
    // 初始化表单
    initForm();
    
    // 初始化数据表格
    initDataTable();
    
    // 添加页面动画
    addPageAnimations();
});

/**
 * 初始化表单
 */
function initForm() {
    const form = document.getElementById('exampleForm');
    if (!form) return;

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = {
            name: document.getElementById('name').value,
            email: document.getElementById('email').value,
            message: document.getElementById('message').value
        };

        // 验证表单
        if (!formData.name || !formData.email || !formData.message) {
            Utils.showMessage('请填写所有必填字段', 'warning');
            return;
        }

        if (!Utils.isValidEmail(formData.email)) {
            Utils.showMessage('请输入有效的邮箱地址', 'warning');
            return;
        }

        const submitBtn = form.querySelector('button[type="submit"]');
        Utils.setLoading(submitBtn, true);

        try {
            // 这里调用实际的API
            // const response = await axios.post('/contact', formData);
            
            // 模拟API调用
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            Utils.showMessage('提交成功！', 'success');
            form.reset();
        } catch (error) {
            console.error('Form submit error:', error);
            Utils.showMessage('提交失败，请稍后重试', 'danger');
        } finally {
            Utils.setLoading(submitBtn, false);
        }
    });
}

/**
 * 初始化数据表格
 */
function initDataTable() {
    const tableBody = document.getElementById('dataTable');
    if (!tableBody) return;

    // 模拟数据
    const mockData = [
        { id: 1, name: '项目A', status: 'active' },
        { id: 2, name: '项目B', status: 'pending' },
        { id: 3, name: '项目C', status: 'completed' }
    ];

    // 渲染表格数据
    function renderTable(data) {
        tableBody.innerHTML = data.map(item => `
            <tr>
                <td>${item.id}</td>
                <td>${item.name}</td>
                <td>
                    <span class="badge bg-${getStatusColor(item.status)}">
                        ${getStatusText(item.status)}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm btn-primary me-1" onclick="editItem(${item.id})">
                        <i class="bi bi-pencil"></i> 编辑
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deleteItem(${item.id})">
                        <i class="bi bi-trash"></i> 删除
                    </button>
                </td>
            </tr>
        `).join('');
    }

    // 获取状态颜色
    function getStatusColor(status) {
        const colors = {
            active: 'success',
            pending: 'warning',
            completed: 'info'
        };
        return colors[status] || 'secondary';
    }

    // 获取状态文本
    function getStatusText(status) {
        const texts = {
            active: '进行中',
            pending: '待处理',
            completed: '已完成'
        };
        return texts[status] || status;
    }

    // 加载数据
    loadTableData();

    async function loadTableData() {
        try {
            // 这里调用实际的API
            // const response = await axios.get('/data');
            // renderTable(response.data);
            
            // 模拟API调用
            await new Promise(resolve => setTimeout(resolve, 500));
            renderTable(mockData);
        } catch (error) {
            console.error('Load table data error:', error);
            Utils.showMessage('加载数据失败', 'danger');
        }
    }
}

/**
 * 编辑项目
 */
function editItem(id) {
    Utils.showMessage(`编辑项目 ID: ${id}`, 'info');
    // 这里可以打开编辑模态框或跳转到编辑页面
}

/**
 * 删除项目
 */
function deleteItem(id) {
    if (confirm('确定要删除这个项目吗？')) {
        Utils.showMessage(`删除项目 ID: ${id}`, 'success');
        // 这里调用实际的删除API
        // axios.delete(`/data/${id}`)
    }
}

/**
 * 添加页面动画
 */
function addPageAnimations() {
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
        card.classList.add('fade-in');
    });
}

/**
 * 页面滚动到顶部
 */
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// 监听滚动，显示返回顶部按钮
let scrollTopBtn = null;
window.addEventListener('scroll', function() {
    if (window.pageYOffset > 300) {
        if (!scrollTopBtn) {
            scrollTopBtn = document.createElement('button');
            scrollTopBtn.className = 'btn btn-primary position-fixed';
            scrollTopBtn.style.cssText = 'bottom: 30px; right: 30px; z-index: 1000; border-radius: 50%; width: 50px; height: 50px;';
            scrollTopBtn.innerHTML = '<i class="bi bi-arrow-up"></i>';
            scrollTopBtn.onclick = scrollToTop;
            document.body.appendChild(scrollTopBtn);
        }
        scrollTopBtn.style.display = 'block';
    } else if (scrollTopBtn) {
        scrollTopBtn.style.display = 'none';
    }
});

// 导出函数到全局
window.editItem = editItem;
window.deleteItem = deleteItem;
window.scrollToTop = scrollToTop;