// Products Page JavaScript

let allProducts = [];
let currentFilter = 'all';

// Initialize Products Page
document.addEventListener('DOMContentLoaded', () => {
    loadAllProducts();
    checkUrlParams();
});

// Check URL parameters for filtering
function checkUrlParams() {
    const params = new URLSearchParams(window.location.search);
    const category = params.get('category');
    if (category) {
        setTimeout(() => {
            filterProducts(category);
            // Update active filter button
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.remove('active');
                if (btn.textContent.trim() === category || 
                    (category === 'all' && btn.textContent.trim() === 'Tất cả')) {
                    btn.classList.add('active');
                }
            });
        }, 500);
    }
}

// Load All Products
async function loadAllProducts() {
    const container = document.getElementById('productsGrid');
    if (!container) return;

    try {
        const response = await ProductsAPI.getAll();
        
        if (response.success && response.data && response.data.length > 0) {
            allProducts = response.data;
            renderProductsGrid(allProducts);
        } else {
            allProducts = getDemoProducts();
            renderProductsGrid(allProducts);
        }
    } catch (error) {
        console.error('Error loading products:', error);
        allProducts = getDemoProducts();
        renderProductsGrid(allProducts);
    }
}

// Get Demo Products
function getDemoProducts() {
    return [
        {
            id: 1,
            name: 'Hệ Thống Quản Lý Bán Hàng POS',
            description: 'Giải pháp quản lý bán hàng toàn diện với tính năng thanh toán, quản lý kho, báo cáo doanh thu. Hỗ trợ đa chi nhánh và đồng bộ dữ liệu thời gian thực.',
            price: 15000000,
            category_id: { name: 'Website' },
            stock_quantity: 10
        },
        {
            id: 2,
            name: 'Website Thương Mại Điện Tử',
            description: 'Website bán hàng trực tuyến với giỏ hàng, thanh toán online, quản lý đơn hàng. Tích hợp các cổng thanh toán phổ biến.',
            price: 25000000,
            category_id: { name: 'E-Commerce' },
            stock_quantity: 5
        },
        {
            id: 3,
            name: 'Ứng Dụng Mobile iOS/Android',
            description: 'Ứng dụng di động đa nền tảng iOS/Android với UI/UX hiện đại. Sử dụng React Native hoặc Flutter.',
            price: 35000000,
            category_id: { name: 'Mobile App' },
            stock_quantity: 3
        },
        {
            id: 4,
            name: 'Hệ Thống ERP Doanh Nghiệp',
            description: 'Giải pháp quản lý tổng thể doanh nghiệp: nhân sự, kế toán, kho, sản xuất. Tùy chỉnh theo quy mô doanh nghiệp.',
            price: 50000000,
            category_id: { name: 'ERP' },
            stock_quantity: 2
        },
        {
            id: 5,
            name: 'CRM Quản Lý Khách Hàng',
            description: 'Phần mềm quản lý quan hệ khách hàng, tự động hóa bán hàng và marketing. Tích hợp email, SMS marketing.',
            price: 20000000,
            category_id: { name: 'CRM' },
            stock_quantity: 8
        },
        {
            id: 6,
            name: 'Hệ Thống Đặt Lịch Hẹn Online',
            description: 'Giải pháp đặt lịch online cho spa, salon, phòng khám, dịch vụ. Tự động nhắc nhở và quản lý lịch.',
            price: 12000000,
            category_id: { name: 'Website' },
            stock_quantity: 15
        },
        {
            id: 7,
            name: 'Website Giới Thiệu Doanh Nghiệp',
            description: 'Website corporate chuyên nghiệp với thiết kế hiện đại, responsive, SEO friendly.',
            price: 8000000,
            category_id: { name: 'Website' },
            stock_quantity: 20
        },
        {
            id: 8,
            name: 'Hệ Thống Quản Lý Nhà Hàng',
            description: 'Phần mềm quản lý nhà hàng, quán cafe với order, bếp, thu ngân, báo cáo. Hỗ trợ QR menu.',
            price: 18000000,
            category_id: { name: 'ERP' },
            stock_quantity: 7
        },
        {
            id: 9,
            name: 'App Giao Hàng & Logistics',
            description: 'Ứng dụng quản lý giao hàng với tracking realtime, tối ưu lộ trình, báo cáo hiệu suất.',
            price: 40000000,
            category_id: { name: 'Mobile App' },
            stock_quantity: 4
        },
        {
            id: 10,
            name: 'Platform Học Trực Tuyến LMS',
            description: 'Hệ thống quản lý học tập với video, bài kiểm tra, chứng chỉ, thanh toán khóa học.',
            price: 45000000,
            category_id: { name: 'E-Commerce' },
            stock_quantity: 3
        },
        {
            id: 11,
            name: 'Hệ Thống Quản Lý Kho WMS',
            description: 'Phần mềm quản lý kho hàng với barcode, RFID, xuất nhập kho, kiểm kê tự động.',
            price: 30000000,
            category_id: { name: 'ERP' },
            stock_quantity: 5
        },
        {
            id: 12,
            name: 'App Đặt Xe & Di Chuyển',
            description: 'Ứng dụng đặt xe như Grab với matching driver, thanh toán, đánh giá, theo dõi trip.',
            price: 55000000,
            category_id: { name: 'Mobile App' },
            stock_quantity: 2
        }
    ];
}

// Render Products Grid
function renderProductsGrid(products) {
    const container = document.getElementById('productsGrid');
    if (!container) return;

    if (products.length === 0) {
        container.innerHTML = `
            <div class="loading">
                <i class="fas fa-search"></i>
                <p>Không tìm thấy sản phẩm nào</p>
            </div>
        `;
        return;
    }

    container.innerHTML = products.map(product => `
        <div class="product-card" data-id="${product.id}" data-category="${product.category_id?.name || ''}">
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
                    <button class="add-to-cart-btn" onclick='addToCart(${JSON.stringify(product).replace(/'/g, "\\'")})'>
                        <i class="fas fa-cart-plus"></i>
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

// Filter Products
function filterProducts(category, buttonElement) {
    currentFilter = category;
    
    // Update active button
    if (buttonElement) {
        document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
        buttonElement.classList.add('active');
    }

    let filteredProducts;
    if (category === 'all') {
        filteredProducts = allProducts;
    } else {
        filteredProducts = allProducts.filter(p => 
            p.category_id?.name?.toLowerCase().includes(category.toLowerCase())
        );
    }

    renderProductsGrid(filteredProducts);
}

// Search Products
function searchProducts() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase().trim();
    
    let filteredProducts = allProducts.filter(product => {
        const matchesSearch = 
            product.name.toLowerCase().includes(searchTerm) ||
            (product.description || '').toLowerCase().includes(searchTerm) ||
            (product.category_id?.name || '').toLowerCase().includes(searchTerm);
        
        const matchesFilter = currentFilter === 'all' || 
            (product.category_id?.name || '').toLowerCase().includes(currentFilter.toLowerCase());
        
        return matchesSearch && matchesFilter;
    });

    renderProductsGrid(filteredProducts);
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
