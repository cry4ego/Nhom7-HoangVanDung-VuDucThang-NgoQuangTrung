// Main Application JavaScript

// DOM Ready
document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

// Initialize Application
function initApp() {
    loadFeaturedProducts();
    loadCategories();
    initAnimations();
    initMobileMenu();
    initAuthForm();
}

// Load Featured Products
async function loadFeaturedProducts() {
    const container = document.getElementById('featuredProducts');
    if (!container) return;

    try {
        const response = await ProductsAPI.getAll();
        
        if (response.success && response.data && response.data.length > 0) {
            const products = response.data.slice(0, 6); // Get first 6 products
            renderProducts(container, products);
        } else {
            // Show demo products if API fails or returns empty
            renderDemoProducts(container);
        }
    } catch (error) {
        console.error('Error loading products:', error);
        renderDemoProducts(container);
    }
}

// Render Products
function renderProducts(container, products) {
    container.innerHTML = products.map(product => `
        <div class="product-card" data-id="${product.id}">
            <div class="product-image">
                <i class="${getProductIcon(product.category_id?.name)}"></i>
                ${product.stock_quantity < 5 ? '<span class="product-badge">Hot</span>' : ''}
            </div>
            <div class="product-content">
                <span class="product-category">${product.category_id?.name || 'Dự án CNTT'}</span>
                <h3 class="product-title">${product.name}</h3>
                <p class="product-description">${product.description || 'Giải pháp công nghệ thông tin chất lượng cao.'}</p>
                <div class="product-footer">
                    <div class="product-price">
                        ${formatCurrency(product.price)}
                    </div>
                    <button class="add-to-cart-btn" onclick="addToCart(${JSON.stringify(product).replace(/"/g, '&quot;')})">
                        <i class="fas fa-cart-plus"></i>
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

// Demo Products (fallback)
function renderDemoProducts(container) {
    const demoProducts = [
        {
            id: 1,
            name: 'Hệ Thống Quản Lý Bán Hàng POS',
            description: 'Giải pháp quản lý bán hàng toàn diện với tính năng thanh toán, quản lý kho, báo cáo doanh thu.',
            price: 15000000,
            category_id: { name: 'Website' },
            stock_quantity: 10
        },
        {
            id: 2,
            name: 'Website Thương Mại Điện Tử',
            description: 'Website bán hàng trực tuyến với giỏ hàng, thanh toán online, quản lý đơn hàng.',
            price: 25000000,
            category_id: { name: 'E-Commerce' },
            stock_quantity: 5
        },
        {
            id: 3,
            name: 'Ứng Dụng Mobile App',
            description: 'Ứng dụng di động đa nền tảng iOS/Android với UI/UX hiện đại.',
            price: 35000000,
            category_id: { name: 'Mobile App' },
            stock_quantity: 3
        },
        {
            id: 4,
            name: 'Hệ Thống ERP Doanh Nghiệp',
            description: 'Giải pháp quản lý tổng thể doanh nghiệp: nhân sự, kế toán, kho, sản xuất.',
            price: 50000000,
            category_id: { name: 'ERP' },
            stock_quantity: 2
        },
        {
            id: 5,
            name: 'CRM Quản Lý Khách Hàng',
            description: 'Phần mềm quản lý quan hệ khách hàng, tự động hóa bán hàng và marketing.',
            price: 20000000,
            category_id: { name: 'CRM' },
            stock_quantity: 8
        },
        {
            id: 6,
            name: 'Hệ Thống Đặt Lịch Hẹn',
            description: 'Giải pháp đặt lịch online cho spa, salon, phòng khám, dịch vụ.',
            price: 12000000,
            category_id: { name: 'Booking' },
            stock_quantity: 15
        }
    ];
    
    renderProducts(container, demoProducts);
}

// Get Product Icon based on category
function getProductIcon(category) {
    const icons = {
        'Website': 'fas fa-globe',
        'E-Commerce': 'fas fa-shopping-cart',
        'Mobile App': 'fas fa-mobile-alt',
        'ERP': 'fas fa-building',
        'CRM': 'fas fa-users',
        'Booking': 'fas fa-calendar-check',
        'API': 'fas fa-plug',
        'Database': 'fas fa-database',
        'AI/ML': 'fas fa-brain',
        'Cloud': 'fas fa-cloud'
    };
    return icons[category] || 'fas fa-project-diagram';
}

// Add to Cart
function addToCart(product) {
    cart.addItem(product);
}

// Load Categories
async function loadCategories() {
    const container = document.getElementById('categoriesGrid');
    if (!container) return;

    try {
        const response = await CategoriesAPI.getAll();
        
        if (response.success && response.data && response.data.length > 0) {
            renderCategories(container, response.data);
        } else {
            renderDemoCategories(container);
        }
    } catch (error) {
        console.error('Error loading categories:', error);
        renderDemoCategories(container);
    }
}

// Render Categories
function renderCategories(container, categories) {
    container.innerHTML = categories.map(category => `
        <div class="category-card" onclick="filterByCategory('${category.name}')">
            <div class="category-icon">
                <i class="${getProductIcon(category.name)}"></i>
            </div>
            <h4>${category.name}</h4>
            <span class="category-count">${category.description || 'Xem dự án'}</span>
        </div>
    `).join('');
}

// Demo Categories
function renderDemoCategories(container) {
    const demoCategories = [
        { name: 'Website', description: '20+ dự án', icon: 'fas fa-globe' },
        { name: 'Mobile App', description: '15+ dự án', icon: 'fas fa-mobile-alt' },
        { name: 'E-Commerce', description: '25+ dự án', icon: 'fas fa-shopping-cart' },
        { name: 'ERP/CRM', description: '10+ dự án', icon: 'fas fa-building' }
    ];
    
    container.innerHTML = demoCategories.map(category => `
        <div class="category-card" onclick="filterByCategory('${category.name}')">
            <div class="category-icon">
                <i class="${category.icon}"></i>
            </div>
            <h4>${category.name}</h4>
            <span class="category-count">${category.description}</span>
        </div>
    `).join('');
}

// Filter by Category
function filterByCategory(category) {
    window.location.href = `products.html?category=${encodeURIComponent(category)}`;
}

// Toast Notification
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const icons = {
        success: 'fas fa-check-circle',
        error: 'fas fa-exclamation-circle',
        info: 'fas fa-info-circle'
    };

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <i class="${icons[type]}"></i>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    // Auto remove after 3 seconds
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Animations
function initAnimations() {
    // Animate stats on scroll
    const stats = document.querySelectorAll('.stat-number');
    if (stats.length > 0) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    animateNumber(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });

        stats.forEach(stat => observer.observe(stat));
    }
}

function animateNumber(element) {
    const target = parseInt(element.dataset.count);
    const duration = 2000;
    const step = target / (duration / 16);
    let current = 0;

    const timer = setInterval(() => {
        current += step;
        if (current >= target) {
            element.textContent = target + (element.closest('.stat-item')?.querySelector('.stat-label')?.textContent.includes('%') ? '%' : '+');
            clearInterval(timer);
        } else {
            element.textContent = Math.floor(current);
        }
    }, 16);
}

// Mobile Menu
function initMobileMenu() {
    // Create mobile menu if needed
}

function toggleMobileMenu() {
    const nav = document.querySelector('.nav');
    if (nav) {
        nav.classList.toggle('active');
    }
}

// Auth form is now handled by auth.js
function initAuthForm() {
    // Auth form setup is handled in auth.js
}

// Close modals on escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeCart();
        closeAuthModal();
        closeCheckoutModal();
    }
});

// Toggle password visibility
function togglePasswordVisibility(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    
    const icon = input.parentElement.querySelector('.toggle-password i');
    
    if (input.type === 'password') {
        input.type = 'text';
        if (icon) {
            icon.classList.remove('fa-eye');
            icon.classList.add('fa-eye-slash');
        }
    } else {
        input.type = 'password';
        if (icon) {
            icon.classList.remove('fa-eye-slash');
            icon.classList.add('fa-eye');
        }
    }
}

// Scroll Header Effect
window.addEventListener('scroll', () => {
    const header = document.querySelector('.header');
    if (window.scrollY > 50) {
        header.style.boxShadow = '0 2px 20px rgba(0,0,0,0.1)';
    } else {
        header.style.boxShadow = 'var(--shadow-sm)';
    }
});
