# Railway Deployment Guide for GigHalal

## 🚂 Quick Railway Deployment

### Prerequisites
- GitHub account
- Railway account (free tier available)
- Your GigHalal code pushed to GitHub

## Step-by-Step Deployment

### 1. Initial Setup

1. **Connect to Railway**
   ```bash
   # Push your code to GitHub first
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/gighalal.git
   git push -u origin main
   ```

2. **Create Railway Project**
   - Go to https://railway.app
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Authorize GitHub and select your GigHalal repository

### 2. Add PostgreSQL Database

1. In your Railway project dashboard, click "+ New"
2. Select "Database" → "Add PostgreSQL"
3. Railway automatically:
   - Creates a PostgreSQL instance
   - Generates `DATABASE_URL` environment variable
   - Links it to your application

### 3. Configure Environment Variables

In Railway project settings → Variables, add:

```
SECRET_KEY=your-super-secret-key-change-this-to-random-string
FLASK_DEBUG=False
PORT=5000
```

**Generate a secure SECRET_KEY:**
```python
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Deploy

Railway will automatically:
- Detect Python application (via requirements.txt)
- Install dependencies
- Use nixpacks.toml configuration
- Start application with Procfile command
- Provide a public URL like: https://gighalal-production.up.railway.app

## Common Issues & Solutions

### ❌ Error: "Error creating build plan with Railpack"

**Solution**: This is the error you're seeing. It means Railway's build system (Railpack/Nixpacks) can't detect your project correctly.

**Fix Options:**

1. **Add nixpacks.toml** (Already included in your project)
   ```toml
   [phases.setup]
   nixPkgs = ['python311', 'postgresql']
   
   [phases.install]
   cmds = ['pip install --upgrade pip', 'pip install -r requirements.txt']
   
   [start]
   cmd = 'gunicorn app:app --bind 0.0.0.0:$PORT --workers 4'
   ```

2. **Ensure all files are committed**
   ```bash
   git add .
   git commit -m "Add Railway configuration"
   git push
   ```

3. **Manually trigger redeploy** in Railway dashboard

### ❌ Database Connection Error

**Symptoms**: App starts but can't connect to database

**Solution**:
```python
# In app.py (already fixed in your code)
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
```

### ❌ Static Files Not Loading

**Solution**: Railway serves static files automatically with Flask. Ensure:
- `/static` directory exists
- Correct paths in templates: `/static/css/style.css`
- No hardcoded localhost URLs

### ❌ Port Binding Error

**Solution**: Always use environment PORT variable:
```python
port = int(os.environ.get('PORT', 5000))
app.run(host='0.0.0.0', port=port)
```

## Verification Steps

After deployment, verify:

1. **App is running**: Check Railway logs for "Running on http://0.0.0.0:5000"
2. **Database connected**: No SQLAlchemy errors in logs
3. **Static files load**: Visit your URL and check CSS/JS load
4. **API endpoints work**: Test /api/categories, /api/gigs

## Railway Configuration Files

Your project includes these Railway-specific files:

1. **requirements.txt** - Python dependencies
2. **Procfile** - How to run the app
3. **runtime.txt** - Python version
4. **nixpacks.toml** - Build configuration (fixes Railpack error)

## Database Migration

After first deployment:

1. **Railway Shell** (optional, for migrations):
   ```bash
   # In Railway dashboard, click on your service
   # Click "Terminal" or use Railway CLI
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

2. **Auto-initialization** (already in code):
   ```python
   # app.py automatically creates tables on first run
   with app.app_context():
       db.create_all()
   ```

## Monitoring & Logs

1. **View Logs**:
   - Railway Dashboard → Your Service → Logs tab
   - Watch for errors during startup

2. **Check Metrics**:
   - Railway Dashboard → Metrics
   - Monitor CPU, Memory, Network usage

3. **Restart Service**:
   - Railway Dashboard → Service → Settings → Restart

## Environment-Specific Configuration

### Development
```
FLASK_DEBUG=True
DATABASE_URL=sqlite:///gighalal.db
```

### Production (Railway)
```
FLASK_DEBUG=False
DATABASE_URL=postgresql://... (auto-provided)
SECRET_KEY=<generated-secret>
```

## Custom Domain (Optional)

1. In Railway project → Settings → Networking
2. Click "Generate Domain" (free subdomain)
3. Or add custom domain:
   - Click "Custom Domain"
   - Add your domain (e.g., gighalal.com)
   - Update DNS CNAME record

## Scaling

Railway automatically scales based on:
- **Free Tier**: $5 free credit/month, 500 hours
- **Paid Tier**: $5/month, unlimited hours, more resources

To scale:
1. Increase Gunicorn workers in Procfile:
   ```
   web: gunicorn app:app --workers 8 --threads 4
   ```
2. Upgrade Railway plan for more resources

## Rollback

If deployment fails:
1. Railway Dashboard → Deployments
2. Click on previous successful deployment
3. Click "Redeploy"

## Cost Estimation

**Railway Pricing:**
- Free: $5 credit/month (~500 hours)
- Hobby: $5/month (usage-based after free tier)
- Pro: $20/month (includes $20 usage credit)

**GigHalal Estimated Costs:**
- Small (100 users): ~$5-10/month
- Medium (1,000 users): ~$15-25/month
- Large (10,000+ users): ~$50-100/month

## Additional Railway Features

### Environment Variables Management
```bash
# Railway CLI (optional)
railway login
railway link
railway variables set SECRET_KEY="your-secret-key"
```

### Database Backups
- Railway Pro includes automatic daily backups
- Manual backup: Railway Dashboard → Database → Backups

### CI/CD
- Automatic deploys on git push (default)
- Configure in: Settings → Service → Deployment Triggers

## Next Steps

After successful deployment:

1. ✅ Test all features on live URL
2. ✅ Set up custom domain
3. ✅ Configure monitoring alerts
4. ✅ Add SSL certificate (automatic with Railway)
5. ✅ Set up database backups
6. ✅ Plan scaling strategy
7. ✅ Add mobile apps (React Native)

## Support

**Railway Support:**
- Discord: https://discord.gg/railway
- Docs: https://docs.railway.app
- Status: https://status.railway.app

**GigHalal Support:**
- GitHub Issues: https://github.com/yourusername/gighalal/issues
- Email: support@gighalal.com

---

**Pro Tip**: Always test your deployment locally first with production-like settings:
```bash
export FLASK_DEBUG=False
export DATABASE_URL=sqlite:///test.db
python app.py
```
