/* ===================================
   主JavaScript文件 - main.js
   =================================== */

// DOM加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    initNavbar();
    initForms();
    initButtons();
});

/**
 * 初始化导航栏
 */
function initNavbar() {
    const toggle = document.getElementById('navbarToggle');
    const nav = document.querySelector('.navbar-nav');
    
    if (toggle && nav) {
        toggle.addEventListener('click', function() {
            nav.classList.toggle('active');
        });
        
        // 点击外部关闭菜单
        document.addEventListener('click', function(e) {
            if (!toggle.contains(e.target) && !nav.contains(e.target)) {
                nav.classList.remove('active');
            }
        });
    }
}

/**
 * 初始化表单
 */
function initForms() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(form);
            const data = Object.fromEntries(formData);
            
            // 显示加载状态
            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn ? submitBtn.textContent : '';
            
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = '提交中...';
            }
            
            try {
                // 这里可以调用API
                // const result = await API.post('/your-endpoint', data);
                
                Utils.showMessage('提交成功', 'success');
                form.reset();
            } catch (error) {
                Utils.showMessage(error.message || '提交失败', 'danger');
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;
                }
            }
        });
    });
}

/**
 * 初始化按钮事件
 */
function initButtons() {
    // 示例：按钮点击事件
    const buttons = document.querySelectorAll('.btn');
    
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            // 可以在这里添加按钮点击处理逻辑
            console.log('Button clicked:', this.textContent);
        });
    });
}

/**
 * 示例：使用API获取数据
 */
async function fetchData() {
    try {
        Utils.showLoading(document.body, true);
        
        // const result = await API.get('/data');
        // console.log('Data:', result);
        
        Utils.showMessage('数据加载成功', 'success');
    } catch (error) {
        Utils.showMessage('数据加载失败', 'danger');
        console.error('Error:', error);
    } finally {
        Utils.showLoading(document.body, false);
    }
}

// 导出函数供全局使用
window.fetchData = fetchData;