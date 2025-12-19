# GigHala - Platform Gig Halal #1 Malaysia

<div align="center">
  <h3>☪ Jana Pendapatan Halal & Berkah dari Rumah</h3>
  <p>Platform gig economy yang menawarkan peluang side hustle halal untuk raih RM800-RM4,000 sebulan</p>
</div>

## 🌟 Features

### Core Marketplace Features
- **Gig Matching Engine**: AI-powered matching based on skills, location, and halal filters
- **Instant Payout Gigs**: Fixed-price tasks with 24-hour payment (RM20-RM300)
- **Brand Partnerships**: Halal-certified brands posting content bounties (RM100-RM500)
- **Micro-Tasks**: Daily quick gigs like reviews and surveys (RM5-RM20)
- **Video Pitches**: 30-second video proposals using integrated editor
- **Halal Verification**: Partnership with JAKIM for halal compliance

### User Types
- **Freelancers**: Find and apply for gigs, build portfolio, earn money
- **Clients**: Post gigs, review applications, manage projects
- **Both**: Users can be both freelancers and clients

### Payment & Monetization
- **15% Commission** on completed gigs
- **Premium Listings**: RM20/month for featured placement
- **Instant Payout**: 24-hour payment via Touch 'n Go or bank transfer
- **Multiple Payment Methods**: iPay88, bank transfer, e-wallets

### Categories
- 🎨 Graphic Design
- ✍️ Writing & Translation
- 🎬 Video Editing
- 📚 Tutoring & Education
- 💻 Tech & Programming
- 📱 Digital Marketing
- 📋 Virtual Assistant
- 📸 Content Creation
- 🎤 Voice Over
- 📊 Data Entry

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL (or SQLite for development)
- Railway account (for deployment)

### Local Development

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/gighala.git
cd gighala
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Initialize database**
```bash
python app.py
```

6. **Run the application**
```bash
python app.py
```

Visit http://localhost:5000 to see the app running!

## 📦 Deployment to Railway

### Step 1: Create Railway Project

1. Go to [Railway.app](https://railway.app)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Connect your GitHub account and select the GigHala repository

### Step 2: Add PostgreSQL Database

1. In your Railway project, click "New"
2. Select "Database" → "Add PostgreSQL"
3. Railway will automatically create a `DATABASE_URL` environment variable

### Step 3: Configure Environment Variables

Add these environment variables in Railway:
- `SECRET_KEY`: Generate a secure random string
- `FLASK_DEBUG`: Set to `False` for production
- `DATABASE_URL`: (automatically provided by Railway)

### Step 4: Deploy

Railway will automatically:
- Detect your Python app
- Install dependencies from requirements.txt
- Use the Procfile to start the application
- Assign a public URL

### Common Railway Deployment Issues & Solutions

**Error: "Error creating build plan with Railpack"**
- Solution: Railway should auto-detect Python. If not, add `nixpacks.toml`:
```toml
[phases.setup]
nixPkgs = ['python311']

[phases.install]
cmds = ['pip install -r requirements.txt']

[start]
cmd = 'gunicorn app:app --bind 0.0.0.0:$PORT'
```

**Database Connection Issues**
- Railway uses `postgres://` but SQLAlchemy needs `postgresql://`
- The app.py automatically handles this conversion
- Check DATABASE_URL format in environment variables

**Static Files Not Loading**
- Ensure `/static` directory exists with css/ and js/ subdirectories
- Verify Flask is configured with correct static_folder and static_url_path
- Check browser console for 404 errors

## 🗂️ Project Structure

```
gighala/
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── Procfile               # Railway deployment configuration
├── runtime.txt            # Python version specification
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
├── templates/
│   └── index.html        # Main HTML template
├── static/
│   ├── css/
│   │   └── style.css     # Comprehensive styling
│   ├── js/
│   │   └── app.js        # Frontend JavaScript
│   └── images/           # Image assets
└── README.md             # This file
```

## 🎨 Design Philosophy

GigHala features a distinctive **Malaysian Islamic aesthetic**:

### Color Palette
- **Primary Green** (#0D7C66): Islamic heritage, halal trust
- **Gold Accents** (#D4AF37): Premium quality, value
- **Teal** (#41B3A2): Modern, tech-forward
- **Cream Background** (#FFF8F0): Warm, inviting

### Typography
- **Display Font**: Crimson Pro (serif) - elegant, authoritative
- **Body Font**: Plus Jakarta Sans - modern, readable

### Key Design Elements
- Halal verification badges
- Floating animated gig cards
- Islamic geometric patterns (subtle)
- Gradient overlays with green/teal
- Premium shadows and depth
- Micro-interactions and animations

## 📊 Market Opportunity (2025 Data)

### Market Size & Growth
- **Gig Economy Growth**: 31% YoY in Malaysia
- **Youth Unemployment**: Up 12% - driving gig demand
- **Target Market**: Urban areas (KL, Penang, Johor)
- **User Potential**: 50,000+ freelancers Year 1

### Competitive Advantage
- **Halal-First**: Only platform with JAKIM verification
- **Local Focus**: MYR payments, Malaysian locations, Bahasa interface
- **Lower Fees**: 15% vs Upwork's 20%
- **Instant Payout**: 24-hour payment vs 7-14 days elsewhere
- **Cultural Fit**: Designed for Malaysian Muslim majority

### Revenue Projections
- **Commission Income**: 15% per gig
- **Premium Features**: RM20/month subscriptions
- **Brand Partnerships**: B2B content deals
- **Year 1 Target**: RM800K+ revenue from 50K users

## 🔐 Security Features

- Password hashing with Werkzeug
- Session-based authentication
- CSRF protection (Flask-WTF ready)
- SQL injection prevention (SQLAlchemy ORM)
- XSS prevention (template escaping)
- Secure payment integration ready (iPay88, Touch 'n Go)

## 🤝 Contributing

We welcome contributions! Here's how:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

Having issues? Contact us:
- **Email**: support@gighala.com
- **WhatsApp**: +60123456789
- **Office**: Calmic Sdn Bhd, Johor Bahru, Malaysia

## 🎯 Roadmap

### Phase 1 (Q1 2025) - MVP Launch ✅
- Core marketplace functionality
- User authentication
- Gig posting and applications
- Basic payment integration

### Phase 2 (Q2 2025) - Growth
- Mobile app (iOS/Android with React Native)
- Video pitch feature with CapCut integration
- Advanced AI matching algorithm
- JAKIM halal verification API integration

### Phase 3 (Q3 2025) - Scale
- Brand partnership dashboard
- Referral program automation
- Multi-language support (Bahasa, English, Chinese)
- Advanced analytics and reporting

### Phase 4 (Q4 2025) - Expansion
- Regional expansion (Indonesia, Singapore, Brunei)
- Gig insurance and dispute resolution
- Skills certification program
- Community features (forums, success stories)

## 📈 Success Metrics

### User Engagement
- **Daily Active Users**: Target 5,000+
- **Gig Completion Rate**: Target 85%+
- **Average Earnings**: RM800-RM4,000/month per freelancer
- **Payment Speed**: <24 hours average

### Business Metrics
- **GMV (Gross Merchandise Value)**: Target RM5M+ Year 1
- **Take Rate**: 15% commission
- **User Retention**: 70%+ monthly active users
- **Brand Partnerships**: 50+ halal companies

---

<div align="center">
  <p><strong>Built with ❤️ by Calmic Sdn Bhd</strong></p>
  <p>Empowering Malaysian freelancers with halal opportunities</p>
  <p>☪ Halal • 🇲🇾 Malaysian • 💰 Profitable</p>
</div>
