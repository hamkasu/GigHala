// GigHalal Application
const app = {
    currentUser: null,
    gigs: [],
    categories: [],
    currentGigId: null,
    gigsOffset: 0,
    gigsLimit: 50,

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
    
    // Apply to gig (show form modal instead of prompt)
    applyToGig(gigId) {
        if (!this.currentUser) {
            this.showLogin();
            return;
        }

        this.currentGigId = gigId;
        this.closeModal('gigModal');
        const modal = document.getElementById('applyModal');
        modal.classList.add('active');
    },

    // Handle apply form submission
    async handleApplyToGig(event) {
        event.preventDefault();
        const form = event.target;
        const formData = new FormData(form);

        const data = {
            cover_letter: formData.get('cover_letter'),
            proposed_price: parseFloat(formData.get('proposed_price'))
        };

        try {
            const response = await fetch(`/api/gigs/${this.currentGigId}/apply`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok) {
                alert('Application submitted successfully!');
                this.closeModal('applyModal');
                form.reset();
                this.loadGigs();
            } else {
                alert('Error: ' + result.error);
            }
        } catch (error) {
            console.error('Error applying to gig:', error);
            alert('Error submitting application. Please try again.');
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
                alert('Login berjaya! Selamat datang, ' + result.user.username);
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
        document.getElementById('guestNav').style.display = 'none';
        document.getElementById('userNav').style.display = 'flex';
    },

    // Logout
    async handleLogout() {
        try {
            await fetch('/api/logout', { method: 'POST' });
            this.currentUser = null;
            document.getElementById('guestNav').style.display = 'flex';
            document.getElementById('userNav').style.display = 'none';
            this.hideAllPages();
            alert('Logout berjaya!');
            window.location.reload();
        } catch (error) {
            console.error('Logout error:', error);
        }
    },

    // Show create gig modal
    showCreateGig() {
        if (!this.currentUser) {
            this.showLogin();
            return;
        }

        // Populate category dropdown
        const select = document.getElementById('createGigCategory');
        select.innerHTML = '<option value="">Pilih kategori</option>' +
            this.categories.map(cat => `<option value="${cat.id}">${cat.name}</option>`).join('');

        const modal = document.getElementById('createGigModal');
        modal.classList.add('active');
    },

    // Handle create gig form submission
    async handleCreateGig(event) {
        event.preventDefault();
        const form = event.target;
        const formData = new FormData(form);

        const data = {
            title: formData.get('title'),
            description: formData.get('description'),
            category: formData.get('category'),
            budget_min: parseFloat(formData.get('budget_min')),
            budget_max: parseFloat(formData.get('budget_max')),
            duration: formData.get('duration'),
            location: formData.get('location'),
            deadline: formData.get('deadline'),
            is_remote: formData.get('is_remote') === 'on',
            halal_compliant: formData.get('halal_compliant') === 'on',
            is_instant_payout: formData.get('is_instant_payout') === 'on'
        };

        try {
            const response = await fetch('/api/gigs', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok) {
                alert('Gig berjaya dipost!');
                this.closeModal('createGigModal');
                form.reset();
                this.loadGigs();
            } else {
                alert('Error: ' + result.error);
            }
        } catch (error) {
            console.error('Error creating gig:', error);
            alert('Error creating gig. Please try again.');
        }
    },

    // Show profile modal
    async showProfile() {
        if (!this.currentUser) {
            this.showLogin();
            return;
        }

        try {
            const response = await fetch('/api/profile');
            const profile = await response.json();

            document.getElementById('profile_full_name').value = profile.full_name || '';
            document.getElementById('profile_phone').value = profile.phone || '';
            document.getElementById('profile_location').value = profile.location || '';
            document.getElementById('profile_bio').value = profile.bio || '';
            document.getElementById('profile_skills').value = profile.skills ? profile.skills.join(', ') : '';

            const modal = document.getElementById('profileModal');
            modal.classList.add('active');
        } catch (error) {
            console.error('Error loading profile:', error);
        }
    },

    // Handle profile update
    async handleUpdateProfile(event) {
        event.preventDefault();
        const form = event.target;
        const formData = new FormData(form);

        const skillsString = formData.get('skills');
        const skills = skillsString ? skillsString.split(',').map(s => s.trim()) : [];

        const data = {
            full_name: formData.get('full_name'),
            phone: formData.get('phone'),
            location: formData.get('location'),
            bio: formData.get('bio'),
            skills: skills
        };

        try {
            const response = await fetch('/api/profile', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok) {
                alert('Profil berjaya dikemaskini!');
                this.closeModal('profileModal');
                this.checkAuth();
            } else {
                alert('Error: ' + result.error);
            }
        } catch (error) {
            console.error('Error updating profile:', error);
            alert('Error updating profile. Please try again.');
        }
    },

    // Show dashboard
    async showDashboard() {
        if (!this.currentUser) {
            this.showLogin();
            return;
        }

        this.hideAllPages();
        document.getElementById('dashboardPage').style.display = 'block';

        try {
            const response = await fetch('/api/dashboard');
            const data = await response.json();

            // Update stats
            document.getElementById('dash_earnings').textContent = `RM ${data.user.total_earnings.toFixed(2)}`;
            document.getElementById('dash_completed').textContent = data.user.completed_gigs;
            document.getElementById('dash_rating').textContent = `${data.user.rating.toFixed(1)} ⭐`;

            // Render posted gigs
            const postedGigsList = document.getElementById('postedGigsList');
            if (data.posted_gigs.length === 0) {
                postedGigsList.innerHTML = '<p style="color: var(--text-gray);">Tiada gig dipost lagi.</p>';
            } else {
                postedGigsList.innerHTML = data.posted_gigs.map(gig => `
                    <div class="gig-card" style="margin-bottom: 16px;">
                        <h3>${this.escapeHtml(gig.title)}</h3>
                        <p>Status: <strong>${gig.status}</strong></p>
                        <p>Budget: RM ${gig.budget_min}-${gig.budget_max}</p>
                        <p>Aplikasi: ${gig.applications}</p>
                        <button class="btn-primary" onclick="app.viewGigApplications(${gig.id})">Lihat Aplikasi</button>
                    </div>
                `).join('');
            }

            // Render applications
            const applicationsList = document.getElementById('applicationsList');
            if (data.applications.length === 0) {
                applicationsList.innerHTML = '<p style="color: var(--text-gray);">Tiada aplikasi lagi.</p>';
            } else {
                applicationsList.innerHTML = data.applications.map(app => `
                    <div class="gig-card" style="margin-bottom: 16px;">
                        <h3>${this.escapeHtml(app.gig_title)}</h3>
                        <p>Status: <strong>${app.status}</strong></p>
                        <p>Harga Cadangan: RM ${app.proposed_price}</p>
                        <button class="btn-secondary" onclick="app.showGigDetails(${app.gig_id})">Lihat Gig</button>
                    </div>
                `).join('');
            }

            // Render transactions
            const transactionsList = document.getElementById('transactionsList');
            if (data.transactions.length === 0) {
                transactionsList.innerHTML = '<p style="color: var(--text-gray);">Tiada transaksi lagi.</p>';
            } else {
                transactionsList.innerHTML = data.transactions.map(t => `
                    <div class="gig-card" style="margin-bottom: 16px;">
                        <p>Jumlah: RM ${t.amount.toFixed(2)}</p>
                        <p>Status: <strong>${t.status}</strong></p>
                        <p>Kaedah: ${t.payment_method || 'N/A'}</p>
                        <p style="font-size: 14px; color: var(--text-gray);">${new Date(t.transaction_date).toLocaleString('ms-MY')}</p>
                    </div>
                `).join('');
            }
        } catch (error) {
            console.error('Error loading dashboard:', error);
            alert('Error loading dashboard');
        }
    },

    // View gig applications
    async viewGigApplications(gigId) {
        try {
            const response = await fetch(`/api/gigs/${gigId}/applications`);
            const applications = await response.json();

            const modal = document.getElementById('gigApplicationsModal');
            const list = document.getElementById('gigApplicationsList');

            if (applications.length === 0) {
                list.innerHTML = '<p style="color: var(--text-gray);">Tiada aplikasi lagi.</p>';
            } else {
                list.innerHTML = applications.map(app => `
                    <div class="gig-card" style="margin-bottom: 16px;">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <div>
                                <h3>${this.escapeHtml(app.freelancer.username)}</h3>
                                <p>Rating: ${app.freelancer.rating} ⭐ | Completed: ${app.freelancer.completed_gigs} gigs</p>
                                <p>Skills: ${app.freelancer.skills.join(', ') || 'N/A'}</p>
                                <p><strong>Harga Cadangan: RM ${app.proposed_price}</strong></p>
                                ${app.cover_letter ? `<p style="margin-top: 12px;">${this.escapeHtml(app.cover_letter)}</p>` : ''}
                            </div>
                            <div>
                                ${app.status === 'pending' ? `
                                    <button class="btn-primary" onclick="app.acceptApplication(${app.id})" style="margin-bottom: 8px; width: 100%;">Terima</button>
                                    <button class="btn-secondary" onclick="app.rejectApplication(${app.id})">Tolak</button>
                                ` : `<span class="badge">${app.status}</span>`}
                            </div>
                        </div>
                    </div>
                `).join('');
            }

            modal.classList.add('active');
        } catch (error) {
            console.error('Error loading applications:', error);
        }
    },

    // Accept application
    async acceptApplication(appId) {
        if (!confirm('Terima aplikasi ini?')) return;

        try {
            const response = await fetch(`/api/applications/${appId}/accept`, {
                method: 'POST'
            });

            if (response.ok) {
                alert('Aplikasi diterima!');
                this.closeModal('gigApplicationsModal');
                this.showDashboard();
            }
        } catch (error) {
            console.error('Error accepting application:', error);
        }
    },

    // Reject application
    async rejectApplication(appId) {
        if (!confirm('Tolak aplikasi ini?')) return;

        try {
            const response = await fetch(`/api/applications/${appId}/reject`, {
                method: 'POST'
            });

            if (response.ok) {
                alert('Aplikasi ditolak.');
                this.closeModal('gigApplicationsModal');
                this.showDashboard();
            }
        } catch (error) {
            console.error('Error rejecting application:', error);
        }
    },

    // Show admin dashboard
    async showAdminDashboard() {
        if (!this.currentUser) {
            this.showLogin();
            return;
        }

        this.hideAllPages();
        document.getElementById('adminPage').style.display = 'block';

        try {
            // Load stats
            const statsResponse = await fetch('/api/admin/stats');
            const stats = await statsResponse.json();

            const adminStats = document.getElementById('adminStats');
            adminStats.innerHTML = `
                <div class="stat-card"><div class="stat-label">Total Users</div><div class="stat-value">${stats.total_users}</div></div>
                <div class="stat-card"><div class="stat-label">Total Gigs</div><div class="stat-value">${stats.total_gigs}</div></div>
                <div class="stat-card"><div class="stat-label">Active Gigs</div><div class="stat-value">${stats.active_gigs}</div></div>
                <div class="stat-card"><div class="stat-label">Completed</div><div class="stat-value">${stats.completed_gigs}</div></div>
                <div class="stat-card"><div class="stat-label">Applications</div><div class="stat-value">${stats.total_applications}</div></div>
                <div class="stat-card"><div class="stat-label">Revenue</div><div class="stat-value">RM ${stats.total_revenue.toFixed(2)}</div></div>
                <div class="stat-card"><div class="stat-label">Paid Out</div><div class="stat-value">RM ${stats.total_paid_out.toFixed(2)}</div></div>
            `;

            // Load users
            const usersResponse = await fetch('/api/admin/users');
            const users = await usersResponse.json();

            const usersList = document.getElementById('adminUsersList');
            usersList.innerHTML = users.slice(0, 10).map(user => `
                <div class="gig-card" style="margin-bottom: 12px;">
                    <p><strong>${this.escapeHtml(user.username)}</strong> (${user.email})</p>
                    <p>${user.user_type} | ⭐ ${user.rating} | RM ${user.total_earnings}</p>
                    <button class="btn-secondary" onclick="app.toggleUserVerification(${user.id})" style="margin-top: 8px;">
                        ${user.is_verified ? 'Unverify' : 'Verify'}
                    </button>
                </div>
            `).join('');

            // Load gigs
            const gigsResponse = await fetch('/api/admin/gigs');
            const gigs = await gigsResponse.json();

            const gigsList = document.getElementById('adminGigsList');
            gigsList.innerHTML = gigs.slice(0, 10).map(gig => `
                <div class="gig-card" style="margin-bottom: 12px;">
                    <p><strong>${this.escapeHtml(gig.title)}</strong></p>
                    <p>${gig.category} | ${gig.status}</p>
                    <p>RM ${gig.budget_min}-${gig.budget_max} | 📝 ${gig.applications}</p>
                </div>
            `).join('');
        } catch (error) {
            console.error('Error loading admin dashboard:', error);
            alert('Error loading admin dashboard. You may not have admin permissions.');
        }
    },

    // Toggle user verification
    async toggleUserVerification(userId) {
        try {
            const response = await fetch(`/api/admin/users/${userId}/verify`, {
                method: 'POST'
            });

            if (response.ok) {
                alert('User verification toggled');
                this.showAdminDashboard();
            }
        } catch (error) {
            console.error('Error toggling verification:', error);
        }
    },

    // Hide all pages
    hideAllPages() {
        document.getElementById('dashboardPage').style.display = 'none';
        document.getElementById('adminPage').style.display = 'none';
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
    async loadMoreGigs() {
        this.gigsOffset += this.gigsLimit;

        try {
            const filters = {};
            const search = document.getElementById('searchInput');
            if (search && search.value) filters.search = search.value;

            const category = document.getElementById('categoryFilter');
            if (category && category.value) filters.category = category.value;

            const location = document.getElementById('locationFilter');
            if (location && location.value) filters.location = location.value;

            const halal = document.getElementById('halalFilter');
            if (halal) filters.halal_only = halal.checked ? 'true' : 'false';

            const params = new URLSearchParams(filters);
            const response = await fetch(`/api/gigs?${params}`);
            const newGigs = await response.json();

            if (newGigs.length > 0) {
                this.gigs = [...this.gigs, ...newGigs];
                this.renderGigs();
            } else {
                alert('Tiada lagi gig untuk dipaparkan');
            }
        } catch (error) {
            console.error('Error loading more gigs:', error);
        }
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
