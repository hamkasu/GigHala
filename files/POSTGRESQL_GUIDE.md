# PostgreSQL Database Guide for GigHalal

## Environment Variable
Your PostgreSQL connection string should be set as:
```
DATABASE_URL=postgresql://username:password@host:port/database_name
```

## SQL Query Commands

### Connect to PostgreSQL (Command Line)
```bash
# Using psql
psql $DATABASE_URL

# Or with explicit parameters
psql -h hostname -U username -d database_name -p 5432
```

### Common SQL Queries

#### View All Tables
```sql
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
```

#### View Table Structure
```sql
\d table_name
-- or
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'user';
```

#### User Queries
```sql
-- List all users
SELECT id, username, email, user_type, location, rating, created_at FROM "user";

-- Find user by email
SELECT * FROM "user" WHERE email = 'example@email.com';

-- Count users by type
SELECT user_type, COUNT(*) FROM "user" GROUP BY user_type;
```

#### Gig Queries
```sql
-- List all open gigs
SELECT id, title, category, budget_min, budget_max, location, created_at 
FROM gig WHERE status = 'open' ORDER BY created_at DESC;

-- Gigs by category
SELECT * FROM gig WHERE category = 'design';

-- Gig statistics
SELECT 
    COUNT(*) as total_gigs,
    COUNT(*) FILTER (WHERE status = 'open') as open_gigs,
    AVG(budget_max) as avg_budget
FROM gig;
```

#### Application Queries
```sql
-- View applications for a gig
SELECT a.*, u.username 
FROM application a 
JOIN "user" u ON a.freelancer_id = u.id 
WHERE a.gig_id = 1;

-- Application status counts
SELECT status, COUNT(*) FROM application GROUP BY status;
```

#### Transaction Queries
```sql
-- Total earnings
SELECT SUM(amount) as total, SUM(net_amount) as net_total FROM transaction;

-- Earnings by user
SELECT u.username, SUM(t.net_amount) as earnings
FROM transaction t
JOIN "user" u ON t.freelancer_id = u.id
WHERE t.status = 'completed'
GROUP BY u.username;
```

## Using Flask Shell

```bash
# Start Flask shell
flask shell
```

```python
# In Flask shell
from app import db, User, Gig, Application, Transaction

# Query users
users = User.query.all()
for u in users:
    print(f"{u.id}: {u.username} - {u.email}")

# Query open gigs
open_gigs = Gig.query.filter_by(status='open').all()

# Add new user
new_user = User(username='test', email='test@test.com', password_hash='...')
db.session.add(new_user)
db.session.commit()

# Raw SQL query
result = db.session.execute(db.text("SELECT * FROM gig LIMIT 5"))
for row in result:
    print(row)
```

## Railway PostgreSQL

Railway provides PostgreSQL through their plugin. After adding PostgreSQL:

1. Railway automatically sets `DATABASE_URL` environment variable
2. Access via Railway Dashboard > Your Project > PostgreSQL plugin
3. Use the "Connect" tab for connection details

### Railway CLI Commands
```bash
# Connect to Railway PostgreSQL
railway connect postgres

# Run raw SQL
railway run psql $DATABASE_URL -c "SELECT * FROM \"user\";"
```
