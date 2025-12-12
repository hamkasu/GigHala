// GigHalal Application
const app = {
    currentUser: null,
    gigs: [],
    categories: [],
    
    // Initialize app
    async init() {
        console.log('Initializing GigHalal App...');
        await this.loadCategories();
        await this.loadGigs();
        await this.loadStats();
        this.setupEventListeners();
        this.checkAuth();
    },
    
    // Check if user is logged in
    checkAuth() {
        fetch('/api/profile')
            .then(response => {
                if (response.ok) {
                    return response.json();
                }
                return null;
            })
            .then(data => {
                if (data) {
                    this.currentUser = data;
                    this.updateUIForLoggedInUser();
                }
            })
            .catch(error => console.error('Auth check failed:', error));
    },
    
    // Load categories
    async loadCategories() {
        try {
            const response = await fetch('/api/categories');
            this.categories = await response.json();
            this.renderCategories();
            this.populateCategoryFilters();
        } catch (error) {
            console.error('Error loading categories:', error);
        }
    },
    
    // Render categories grid
    renderCategories() {
        const grid = document.getElementById('categoriesGrid');
        if (!grid) return;
        
        grid.innerHTML = this.categories.map(cat => `
            <div class="category-card" onclick="app.filterByCategory('${cat.id}')">
                <span class="category-icon">${cat.icon}</span>
                <div class="category-name">${cat.name}</div>
            </div>
        `).join('');
    },
    
    // Populate category filters
    populateCategoryFilters() {
        const select = document.getElementById('categoryFilter');
        if (!select) return;
        
        select.innerHTML = '<option value="">Semua Kategori</option>' +
            this.categories.map(cat => 
                `<option value="${cat.id}">${cat.name}</option>`
            ).join('');
    },
    
    // Load gigs
    async loadGigs(filters = {}) {
        try {
            const params = new URLSearchParams(filters);
            const response = await fetch(`/api/gigs?${params}`);
            this.gigs = await response.json();
            this.renderGigs();
        } catch (error) {
            console.error('Error loading gigs:', error);
        }
    },
    
    // Render gigs grid
    renderGigs() {
        const grid = document.getElementById('gigsGrid');
        if (!grid) return;
        
        if (this.gigs.length === 0) {
            grid.innerHTML = '<p style="text-align: center; color: var(--text-gray); grid-column: 1/-1;">Tiada gig dijumpai. Cuba filter yang berbeza.</p>';
            return;
        }
        
        grid.innerHTML = this.gigs.map(gig => {
            const badges = [];
            if (gig.halal_verified) badges.push('<span class="badge badge-halal">☪ HALAL</span>');
            if (gig.is_instant_payout) badges.push('<span class="badge badge-instant">⚡ INSTANT</span>');
            if (gig.is_brand_partnership) badges.push('<span class="badge badge-brand">🌟 BRAND</span>');
            if (gig.is_remote) badges.push('<span class="badge badge-remote">🌐 REMOTE</span>');
            
            return `
                <div class="gig-card" onclick="app.showGigDetails(${gig.id})">
                    <div class="gig-header">
                        <div class="gig-badges">
                            ${badges.join('')}
                        </div>
                    </div>
                    <h3 class="gig-title">${this.escapeHtml(gig.title)}</h3>
                    <p class="gig-description">${this.escapeHtml(gig.description)}</p>
                    <div class="gig-meta">
                        <span class="gig-meta-item">📍 ${gig.location || 'Remote'}</span>
                        <span class="gig-meta-item">⏱️ ${gig.duration || 'Flexible'}</span>
                    </div>
                    <div class="gig-footer">
                        <div class="gig-price">RM ${gig.budget_min}-${gig.budget_max}</div>
                        <div class="gig-stats">
                            <span>👁️ ${gig.views}</span>
                            <span>📝 ${gig.applications}</span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    },
    
    // Show gig details modal
    async showGigDetails(gigId) {
        try {
            const response = await fetch(`/api/gigs/${gigId}`);
            const gig = await response.json();
            
            const modal = document.getElementById('gigModal');
            const details = document.getElementById('gigDetails');
            
            const badges = [];
            if (gig.halal_verified) badges.push('<span class="badge badge-halal">☪ HALAL VERIFIED</span>');
            if (gig.is_instant_payout) badges.push('<span class="badge badge-instant">⚡ INSTANT PAYOUT</span>');
            if (gig.is_brand_partnership) badges.push('<span class="badge badge-brand">🌟 BRAND PARTNERSHIP</span>');
            if (gig.is_remote) badges.push('<span class="badge badge-remote">🌐 REMOTE</span>');
            
            details.innerHTML = `
                <div style="margin-bottom: 24px;">
                    <div style="display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap;">
                        ${badges.join('')}
                    </div>
                    <h2 style="font-size: 32px; font-family: var(--font-display); margin-bottom: 16px;">${this.escapeHtml(gig.title)}</h2>
                    <div style="display: flex; gap: 24px; color: var(--text-gray); margin-bottom: 24px;">
                        <span>📍 ${gig.location || 'Remote'}</span>
                        <span>⏱️ ${gig.duration || 'Flexible'}</span>
                        <span>📅 ${new Date(gig.created_at).toLocaleDateString('ms-MY')}</span>
                    </div>
                </div>
                
                <div style="background: var(--soft-cream); padding: 24px; border-radius: 16px; margin-bottom: 24px;">
                    <div style="font-size: 14px; color: var(--text-gray); margin-bottom: 8px;">Budget</div>
                    <div style="font-size: 36px; font-weight: 800; color: var(--primary-green); font-family: var(--font-display);">
                        RM ${gig.budget_min} - RM ${gig.budget_max}
                    </div>
                </div>
                
                <div style="margin-bottom: 24px;">
                    <h3 style="font-size: 20px; font-weight: 700; margin-bottom: 12px;">Deskripsi</h3>
                    <p style="line-height: 1.8; color: var(--text-dark);">${this.escapeHtml(gig.description)}</p>
                </div>
                
                <div style="margin-bottom: 24px;">
                    <h3 style="font-size: 20px; font-weight: 700; margin-bottom: 12px;">Maklumat Client</h3>
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <img src="https://via.placeholder.com/50" alt="${this.escapeHtml(gig.client.username)}" style="width: 50px; height: 50px; border-radius: 50%;">
                        <div>
                            <div style="font-weight: 600;">${this.escapeHtml(gig.client.username)}</div>
                            <div style="font-size: 14px; color: var(--text-gray);">Rating: ${gig.client.rating} ⭐</div>
                        </div>
                        ${gig.client.is_verified ? '<span class="badge" style="margin-left: auto;">✓ VERIFIED</span>' : ''}
                    </div>
                </div>
                
                <div style="display: flex; gap: 16px; padding-top: 24px; border-top: 1px solid var(--border-light);">
                    <button class="btn-modal-primary" onclick="app.applyToGig(${gig.id})" style="flex: 1;">
                        Apply Sekarang
                    </button>
                    <button class="btn-secondary" onclick="app.closeModal('gigModal')" style="padding: 14px 32px;">
                        Tutup
                    </button>
                </div>
                
                <div style="margin-top: 24px; text-align: center; color: var(--text-gray); font-size: 14px;">
                    👁️ ${gig.views} views  •  📝 ${gig.applications} applications
                </div>
            `;
            
            modal.classList.add('active');
        } catch (error) {
            console.error('Error loading gig details:', error);
            alert('Error loading gig details. Please try again.');
        }
    },
    
    // Apply to gig
    applyToGig(gigId) {
        if (!this.currentUser) {
            this.showLogin();
            return;
        }
        
        const coverLetter = prompt('Masukkan cover letter anda (optional):');
        const proposedPrice = prompt('Harga cadangan anda (RM):');
        
        if (proposedPrice) {
            fetch(`/api/gigs/${gigId}/apply`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    cover_letter: coverLetter,
                    proposed_price: parseFloat(proposedPrice)
                })
            })
            .then(response => response.json())
            .then(data => {
                alert('Application submitted successfully!');
                this.closeModal('gigModal');
                this.loadGigs();
            })
            .catch(error => {
                console.error('Error applying to gig:', error);
                alert('Error submitting application. Please try again.');
            });
        }
    },
    
    // Load statistics
    async loadStats() {
        try {
            const response = await fetch('/api/stats');
            const stats = await response.json();
            
            const gigsElement = document.getElementById('totalGigs');
            if (gigsElement) {
                gigsElement.textContent = stats.active_gigs.toLocaleString();
            }
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    },
    
    // Setup event listeners
    setupEventListeners() {
        // Search input
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            let debounceTimer;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    this.applyFilters();
                }, 500);
            });
        }
        
        // Category filter
        const categoryFilter = document.getElementById('categoryFilter');
        if (categoryFilter) {
            categoryFilter.addEventListener('change', () => this.applyFilters());
        }
        
        // Location filter
        const locationFilter = document.getElementById('locationFilter');
        if (locationFilter) {
            locationFilter.addEventListener('change', () => this.applyFilters());
        }
        
        // Halal filter
        const halalFilter = document.getElementById('halalFilter');
        if (halalFilter) {
            halalFilter.addEventListener('change', () => this.applyFilters());
        }
        
        // Close modals on outside click
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                e.target.classList.remove('active');
            }
        });
    },
    
    // Apply all filters
    applyFilters() {
        const filters = {};
        
        const search = document.getElementById('searchInput');
        if (search && search.value) filters.search = search.value;
        
        const category = document.getElementById('categoryFilter');
        if (category && category.value) filters.category = category.value;
        
        const location = document.getElementById('locationFilter');
        if (location && location.value) filters.location = location.value;
        
        const halal = document.getElementById('halalFilter');
        if (halal) filters.halal_only = halal.checked ? 'true' : 'false';
        
        this.loadGigs(filters);
    },
    
    // Filter by category
    filterByCategory(categoryId) {
        const categoryFilter = document.getElementById('categoryFilter');
        if (categoryFilter) {
            categoryFilter.value = categoryId;
            this.applyFilters();
        }
        this.scrollTo('cari-gig');
    },
    
    // Show login modal
    showLogin() {
        const modal = document.getElementById('loginModal');
        modal.classList.add('active');
    },
    
    // Show register modal
    showRegister() {
        const modal = document.getElementById('registerModal');
        modal.classList.add('active');
    },
    
    // Close modal
    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        modal.classList.remove('active');
    },
    
    // Switch to register modal
    switchToRegister() {
        this.closeModal('loginModal');
        this.showRegister();
    },
    
    // Switch to login modal
    switchToLogin() {
        this.closeModal('registerModal');
        this.showLogin();
    },
    
    // Handle login form submission
    async handleLogin(event) {
        event.preventDefault();
        const form = event.target;
        const formData = new FormData(form);
        
        const data = {
            email: formData.get('email'),
            password: formData.get('password')
        };
        
        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.currentUser = result.user;
                this.updateUIForLoggedInUser();
                this.closeModal('loginModal');
                // Redirect to personalized dashboard
                window.location.href = '/dashboard';
            } else {
                alert('Login gagal: ' + result.error);
            }
        } catch (error) {
            console.error('Login error:', error);
            alert('Error during login. Please try again.');
        }
    },
    
    // Handle register form submission
    async handleRegister(event) {
        event.preventDefault();
        const form = event.target;
        const formData = new FormData(form);
        
        const data = {
            username: formData.get('username'),
            email: formData.get('email'),
            password: formData.get('password'),
            full_name: formData.get('full_name'),
            phone: formData.get('phone'),
            location: formData.get('location'),
            user_type: formData.get('user_type')
        };
        
        try {
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.currentUser = result.user;
                this.updateUIForLoggedInUser();
                this.closeModal('registerModal');
                alert('Pendaftaran berjaya! Selamat datang, ' + result.user.username);
            } else {
                alert('Pendaftaran gagal: ' + result.error);
            }
        } catch (error) {
            console.error('Registration error:', error);
            alert('Error during registration. Please try again.');
        }
    },
    
    // Update UI for logged in user
    updateUIForLoggedInUser() {
        console.log('User logged in:', this.currentUser);
        // Update navigation to show profile link
        // This would be implemented based on your UI requirements
    },
    
    // Scroll to section
    scrollTo(sectionId) {
        const element = document.getElementById(sectionId);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth' });
        }
    },
    
    // Toggle mobile menu
    toggleMobileMenu() {
        const navLinks = document.querySelector('.nav-links');
        if (navLinks) {
            navLinks.style.display = navLinks.style.display === 'flex' ? 'none' : 'flex';
        }
    },
    
    // Load more gigs
    loadMoreGigs() {
        alert('Load more functionality would paginate through more gigs');
        // Implementation would involve pagination
    },
    
    // Escape HTML to prevent XSS
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    app.init();
});

// Export for use in other scripts
window.app = app;
