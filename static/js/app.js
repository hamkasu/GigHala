// GigHala Application
const app = {
    currentUser: null,
    gigs: [],
    categories: [],
    
    // Category name translations (English -> Malay)
    categoryTranslations: {
        'Design & Creative': 'Reka Bentuk & Kreatif',
        'Writing & Translation': 'Penulisan & Terjemahan',
        'Video & Animation': 'Video & Animasi',
        'Web Development': 'Pembangunan Web',
        'Digital Marketing': 'Pemasaran Digital',
        'Tutoring & Education': 'Tunjuk Ajar & Pendidikan',
        'Content Creation': 'Penciptaan Kandungan',
        'Admin Support': 'Sokongan Admin',
        'General Works': 'Kerja Am',
        'Virtual Assistant': 'Pembantu Maya',
        'Delivery & Logistics': 'Penghantaran & Logistik',
        'Micro-Tasks & Daily': 'Tugasan Mikro & Harian',
        'Event Management': 'Pengurusan Acara',
        'Caregiving & Services': 'Penjagaan & Perkhidmatan',
        'Photography & Videography': 'Fotografi & Videografi',
        'Other Creative': 'Kreatif Lain',
        'Programming & Tech': 'Pengaturcaraan & Teknologi',
        'Business Consulting': 'Konsultasi Perniagaan',
        'Engineering Services': 'Perkhidmatan Kejuruteraan',
        'Music & Audio': 'Muzik & Audio',
        'Finance & Bookkeeping': 'Kewangan & Simpan Kira',
        'Crafts & Handmade': 'Kerajinan & Buatan Tangan',
        'Home & Garden': 'Rumah & Taman',
        'Life Coaching': 'Bimbingan Hidup',
        'Data Analysis': 'Analisis Data',
        'Pet Services': 'Perkhidmatan Haiwan Peliharaan',
        'Handyman & Repairs': 'Handyman & Pembaikan',
        'Tour Guiding': 'Panduan Lawatan',
        'Event Planning': 'Perancangan Acara',
        'Online Selling': 'Penjualan Dalam Talian',
        'Graphic Design': 'Reka Bentuk Grafik',
        'UI/UX Design': 'Reka Bentuk UI/UX',
        'Illustration & Art': 'Ilustrasi & Seni',
        'Logo Design': 'Reka Bentuk Logo',
        'Fashion Design': 'Reka Bentuk Fesyen',
        'Interior Design': 'Reka Bentuk Dalaman',
        'Content Writing': 'Penulisan Kandungan',
        'Translation Services': 'Perkhidmatan Terjemahan',
        'Proofreading & Editing': 'Penyemakan & Penyuntingan',
        'Resume & Cover Letter': 'Resume & Surat Iringan',
        'Email & Newsletter': 'Emel & Surat Berita',
        'Social Media Copy': 'Salinan Media Sosial',
        'Video Editing': 'Penyuntingan Video',
        'Animation': 'Animasi',
        'Voiceover & Voice Acting': 'Latar Suara',
        'Podcast Production': 'Produksi Podcast',
        'Photography': 'Fotografi',
        'App Development': 'Pembangunan Aplikasi',
        'E-commerce Solutions': 'Penyelesaian E-dagang',
        'Digital Marketing': 'Pemasaran Digital',
        'Social Media Management': 'Pengurusan Media Sosial',
        'Business Consulting': 'Konsultasi Perniagaan',
        'Data Analysis': 'Analisis Data',
        'Tutoring & Lessons': 'Tunjuk Ajar & Pelajaran',
        'Language Teaching': 'Pengajaran Bahasa',
        'Programming & Development': 'Pengaturcaraan & Pembangunan',
        'Engineering & CAD': 'Kejuruteraan & CAD',
        'Virtual Assistance': 'Pembantu Maya',
        'Transcription': 'Transkripsi',
        'Data Entry': 'Kemasukan Data',
        'Bookkeeping & Accounting': 'Simpan Kira & Perakaunan',
        'Legal Document Services': 'Perkhidmatan Dokumen Perundangan',
        'Life & Wellness Coaching': 'Bimbingan Hidup & Kesejahteraan',
        'Personal Styling': 'Penggayaan Peribadi',
        'Pet Services': 'Perkhidmatan Haiwan Peliharaan',
        'Home Repairs & Handyman': 'Pembaikan Rumah & Handyman',
        'Cleaning Services': 'Perkhidmatan Pembersihan',
        'Gardening & Landscaping': 'Perkebunan & Landskap',
        'Crafts & Handmade Items': 'Barangan Kraf & Buatan Tangan',
        'Music & Audio Production': 'Produksi Muzik & Audio',
        'Event Planning & Coordination': 'Perancangan & Koordinasi Acara',
        'Travel Guide & Tours': 'Pemandu Pelancong & Lawatan',
        'General Services': 'Perkhidmatan Am',
        'Design': 'Reka Bentuk',
        'Writing': 'Penulisan',
        'Video': 'Video',
        'Content': 'Kandungan',
        'Web': 'Web',
        'Marketing': 'Pemasaran',
        'Admin': 'Admin',
        'Consulting': 'Konsultasi',
        'Music': 'Muzik',
        'Finance': 'Kewangan',
        'Crafts': 'Kraf',
        'Garden': 'Taman',
        'Coaching': 'Bimbingan',
        'Data': 'Data',
        'Pets': 'Haiwan Peliharaan',
        'Handyman': 'Handyman',
        'Events': 'Acara',
        'Online Selling': 'Penjualan Dalam Talian'
    },
    
    translateCategoryName(name) {
        return this.categoryTranslations[name] || name;
    },
    
    // Initialize app - Optimized to prioritize critical content
    async init() {
        console.log('Initializing GigHala App...');

        // Load critical content first
        this.setupEventListeners();

        // Load categories immediately (needed for UI)
        await this.loadCategories();

        // Defer non-critical API calls using requestIdleCallback or setTimeout
        if ('requestIdleCallback' in window) {
            requestIdleCallback(() => {
                this.loadGigs();
                this.loadStats();
                this.checkAuth();
            }, { timeout: 2000 });
        } else {
            setTimeout(() => {
                this.loadGigs();
                this.loadStats();
                this.checkAuth();
            }, 100);
        }

        this.setupSOCSOCardHover();
    },

    // Setup SOCSO card hover tooltip
    setupSOCSOCardHover() {
        const socsoCard = document.querySelector('.socso-card');
        if (socsoCard) {
            const tooltip = socsoCard.querySelector('.socso-tooltip');
            if (tooltip) {
                socsoCard.addEventListener('mouseenter', () => {
                    tooltip.style.display = 'block';
                });
                socsoCard.addEventListener('mouseleave', () => {
                    tooltip.style.display = 'none';
                });
            }
        }
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
            this.renderNavCategories();
        } catch (error) {
            console.error('Error loading categories:', error);
        }
    },
    
    // Render categories in navigation dropdown
    renderNavCategories() {
        const list = document.getElementById('navCategoriesList');
        const listBase = document.getElementById('navCategoriesListBase');
        
        const html = this.categories.map(cat => `
            <a href="#" class="category-item" onclick="app.filterByCategory('${cat.id}'); return false;">
                <span style="font-size: 18px;">${cat.icon}</span>
                <span>${this.translateCategoryName(cat.name)}</span>
            </a>
        `).join('');

        if (list) list.innerHTML = html;
        if (listBase) listBase.innerHTML = html;
    },
    
    // Render categories grid
    renderCategories() {
        const grid = document.getElementById('categoriesGrid');
        if (!grid) return;
        
        grid.innerHTML = this.categories.map(cat => `
            <div class="category-card" onclick="app.filterByCategory('${cat.id}')">
                <span class="category-icon">${cat.icon}</span>
                <div class="category-name">${this.translateCategoryName(cat.name)}</div>
            </div>
        `).join('');
    },
    
    // Populate category filters
    populateCategoryFilters() {
        const select = document.getElementById('categoryFilter');
        const secondarySelect = document.getElementById('categorySelect');
        
        if (select) {
            select.innerHTML = '<option value="">Semua Kategori</option>' +
                this.categories.map(cat => 
                    `<option value="${cat.id}">${this.translateCategoryName(cat.name)}</option>`
                ).join('');
        }
        
        if (secondarySelect) {
            secondarySelect.innerHTML = '<option value="">Semua Kategori</option>' +
                this.categories.map(cat => 
                    `<option value="${cat.id}">${this.translateCategoryName(cat.name)}</option>`
                ).join('');
        }
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

        // Don't render if we're on the /gigs page (it has its own rendering logic)
        if (window.location.pathname === '/gigs') return;

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
            document.body.classList.add('modal-open');
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
        // Category dropdown toggle
        const categoryTriggers = document.querySelectorAll('.category-trigger');
        const categoryMenus = document.querySelectorAll('.category-menu');
        
        categoryTriggers.forEach((trigger, index) => {
            const menu = categoryMenus[index];
            if (trigger && menu) {
                trigger.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    const isVisible = menu.style.display === 'block';
                    
                    // Close all other menus first
                    categoryMenus.forEach(m => m.style.display = 'none');
                    
                    menu.style.display = isVisible ? 'none' : 'block';
                });
            }
        });

        // Close when clicking outside
        document.addEventListener('click', (e) => {
            categoryMenus.forEach(menu => {
                if (!e.target.closest('.category-dropdown')) {
                    menu.style.display = 'none';
                }
            });
        });

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

                // Check if any modals are still open
                const openModals = document.querySelectorAll('.modal.active');
                if (openModals.length === 0) {
                    document.body.classList.remove('modal-open');
                }
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
        document.body.classList.add('modal-open');
    },

    // Show register modal
    showRegister() {
        const modal = document.getElementById('registerModal');
        modal.classList.add('active');
        document.body.classList.add('modal-open');
        // Setup SOCSO consent field visibility based on user type
        this.setupSOCSOConsentListener();
    },

    // Setup SOCSO consent field visibility listener
    setupSOCSOConsentListener() {
        const userTypeSelect = document.querySelector('select[name="user_type"]');
        const socsoConsentGroup = document.getElementById('socsoConsentGroup');
        const socsoConsent = document.getElementById('socsoConsent');
        
        if (userTypeSelect && socsoConsentGroup && socsoConsent) {
            const updateSOCSOVisibility = () => {
                const userType = userTypeSelect.value;
                if (userType === 'freelancer' || userType === 'both') {
                    socsoConsentGroup.style.display = 'block';
                    socsoConsent.required = true;
                } else {
                    socsoConsentGroup.style.display = 'none';
                    socsoConsent.required = false;
                    socsoConsent.checked = false;
                }
            };
            
            userTypeSelect.addEventListener('change', updateSOCSOVisibility);
            // Initialize on load
            updateSOCSOVisibility();
        }
    },
    
    // Close modal
    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('active');
            modal.style.display = 'none';
        }

        // Check if any modals are still open
        const openModals = document.querySelectorAll('.modal.active');
        if (openModals.length === 0) {
            document.body.classList.remove('modal-open');
        }
    },

    // Handle Login
    async handleLogin(event) {
        event.preventDefault();
        const formData = new FormData(event.target);
        const data = Object.fromEntries(formData.entries());
        const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': csrfToken
                },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                window.location.href = '/dashboard';
            } else {
                const error = await response.json();
                alert(error.message || 'Log masuk gagal');
            }
        } catch (error) {
            console.error('Login error:', error);
            alert('Ralat semasa log masuk');
        }
    },

    // Handle Register
    async handleRegister(event) {
        event.preventDefault();
        const formData = new FormData(event.target);
        const data = Object.fromEntries(formData.entries());
        const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

        try {
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': csrfToken
                },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                window.location.href = '/dashboard';
            } else {
                const error = await response.json();
                alert(error.message || 'Pendaftaran gagal');
            }
        } catch (error) {
            console.error('Register error:', error);
            alert('Ralat semasa pendaftaran');
        }
    },
    
    // Switch to register modal
    switchToRegister() {
        this.closeModal('loginModal');
        this.showRegister();
    },
    
    // Switch to login modal
    switchToLogin() {
        this.closeModal('registerModal');
        this.closeModal('forgotPasswordModal');
        this.showLogin();
    },

    // Switch to forgot password modal
    switchToForgotPassword() {
        this.closeModal('loginModal');
        const modal = document.getElementById('forgotPasswordModal');
        modal.classList.add('active');
        document.body.classList.add('modal-open');
    },

    // Show privacy policy modal
    showPrivacyPolicy(event) {
        if (event) event.preventDefault();
        const modal = document.getElementById('privacyPolicyModal');
        modal.classList.add('active');
        document.body.classList.add('modal-open');
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
                // Check if this is an OAuth-specific error
                if (result.oauth_provider === 'google') {
                    // Show error message
                    alert('Login gagal: ' + result.error);

                    // Highlight the Google login button
                    const googleBtn = document.querySelector('.btn-google');
                    if (googleBtn) {
                        googleBtn.style.animation = 'pulse 1s ease-in-out 3';
                        googleBtn.style.border = '2px solid #4285F4';
                        googleBtn.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

                        // Remove highlight after 3 seconds
                        setTimeout(() => {
                            googleBtn.style.animation = '';
                            googleBtn.style.border = '';
                        }, 3000);
                    }
                } else {
                    alert('Login gagal: ' + result.error);
                }
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

        // Combine first and last name for backend compatibility
        const firstName = formData.get('first_name');
        const lastName = formData.get('last_name');
        const fullName = `${firstName} ${lastName}`.trim();

        const data = {
            username: formData.get('username'),
            email: formData.get('email'),
            password: formData.get('password'),
            full_name: fullName,
            phone: formData.get('phone') || '',
            ic_number: formData.get('ic_number') || '',
            location: formData.get('location') || 'Kuala Lumpur',
            user_type: formData.get('user_type') || 'freelancer',
            privacy_consent: true,
            socso_consent: true
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

    // Handle forgot password form submission
    async handleForgotPassword(event) {
        event.preventDefault();
        const form = event.target;
        const formData = new FormData(form);

        const data = {
            email: formData.get('email')
        };

        try {
            const response = await fetch('/api/forgot-password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok) {
                alert(result.message);
                this.closeModal('forgotPasswordModal');
                form.reset();
            } else {
                alert(result.error || 'Failed to send reset link. Please try again.');
            }
        } catch (error) {
            console.error('Forgot password error:', error);
            alert('An error occurred. Please try again later.');
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
