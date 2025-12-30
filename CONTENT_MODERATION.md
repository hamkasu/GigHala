# Content Moderation System

## Overview

GigHala now includes comprehensive image content moderation to detect and block inappropriate images including pornographic, violent, and gruesome content. This system uses Google Cloud Vision API's SafeSearch feature to analyze all uploaded images in real-time.

## Features

- **Real-time Image Scanning**: All uploaded images are scanned immediately upon upload
- **Multiple Content Type Detection**:
  - Adult/Pornographic content
  - Violent/Gruesome content
  - Racy/Suggestive content
- **Comprehensive Coverage**: Moderation applies to:
  - Gig reference photos
  - Work progress/completion photos
  - Portfolio images
  - Verification documents (IC/Passport)
- **Audit Logging**: All moderation results are logged to database for compliance and auditing
- **Configurable Thresholds**: Adjust sensitivity levels via environment variables
- **Automatic Cleanup**: Rejected images are automatically deleted from the server

## Architecture

### Components

1. **`content_moderation.py`**: Core moderation module
   - `ImageContentModerator`: Main class handling moderation logic
   - `ContentModerationResult`: Result container
   - `moderate_image()`: Convenience function

2. **`ContentModerationLog` Model** (`app.py`): Database model tracking all moderation attempts

3. **Integration Points**: Moderation integrated into 4 upload endpoints:
   - `POST /api/gigs/<gig_id>/gig-photos`
   - `POST /api/gigs/<gig_id>/work-photos`
   - `POST /api/portfolio`
   - `POST /upload_verification_documents`

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `google-cloud-vision>=3.4.0` (added to requirements.txt)

### 2. Set Up Google Cloud Vision API

#### A. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing project
3. Enable the **Cloud Vision API**:
   - Go to "APIs & Services" > "Library"
   - Search for "Cloud Vision API"
   - Click "Enable"

#### B. Create Service Account Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Fill in service account details
4. Grant the role: **"Cloud Vision AI Service Agent"**
5. Click "Done"
6. Click on the created service account
7. Go to "Keys" tab
8. Click "Add Key" > "Create New Key"
9. Choose "JSON" format
10. Download the JSON file
11. Save it securely on your server (e.g., `/opt/gighala/google-cloud-vision-credentials.json`)

**Important**: Keep this file secure and never commit it to version control!

#### C. Set File Permissions

```bash
chmod 600 /path/to/google-cloud-vision-credentials.json
chown your_app_user:your_app_group /path/to/google-cloud-vision-credentials.json
```

### 3. Configure Environment Variables

Update your `.env` file with the following settings:

```bash
# Content Moderation (Image Safety)
CONTENT_MODERATION_ENABLED=true
CONTENT_MODERATION_STRICT=true
GOOGLE_CLOUD_VISION_CREDENTIALS=/path/to/google-cloud-vision-credentials.json

# Optional: Override default thresholds
# ADULT_CONTENT_THRESHOLD=POSSIBLE
# VIOLENCE_THRESHOLD=POSSIBLE
# RACY_CONTENT_THRESHOLD=LIKELY
```

#### Configuration Options

| Variable | Default (Strict) | Default (Normal) | Description |
|----------|-----------------|------------------|-------------|
| `CONTENT_MODERATION_ENABLED` | `true` | `true` | Enable/disable moderation |
| `CONTENT_MODERATION_STRICT` | `true` | `false` | Use strict thresholds |
| `ADULT_CONTENT_THRESHOLD` | `POSSIBLE` | `LIKELY` | Min level to block adult content |
| `VIOLENCE_THRESHOLD` | `POSSIBLE` | `LIKELY` | Min level to block violence |
| `RACY_CONTENT_THRESHOLD` | `LIKELY` | `VERY_LIKELY` | Min level to block racy content |

**Likelihood Levels** (from lowest to highest):
- `UNKNOWN`
- `VERY_UNLIKELY`
- `UNLIKELY`
- `POSSIBLE`
- `LIKELY`
- `VERY_LIKELY`

### 4. Run Database Migration

#### For PostgreSQL:

```bash
psql -U your_db_user -d gighala_db -f migrations/012_add_content_moderation.sql
```

#### For SQLite (Development):

```bash
sqlite3 gighala.db < migrations/012_add_content_moderation_sqlite.sql
```

Or using Python:

```python
from app import app, db
with app.app_context():
    db.create_all()
```

### 5. Verify Installation

Test that moderation is working:

```python
from content_moderation import moderate_image

# Test with a safe image
is_safe, message, details = moderate_image('/path/to/test/image.jpg')
print(f"Safe: {is_safe}, Message: {message}")
print(f"Details: {details}")
```

### 6. Restart Application

```bash
# Using systemd
sudo systemctl restart gighala

# Or if using gunicorn directly
pkill gunicorn
gunicorn app:app -b 0.0.0.0:5000 -w 4
```

## How It Works

### Upload Flow

1. **User uploads image** → File received by Flask
2. **File validation** → Check file type and size
3. **Save to disk** → Store with unique filename
4. **Content moderation** → Scan with Google Vision API
5. **Log result** → Save to `ContentModerationLog` table
6. **Decision**:
   - ✅ **Safe**: Continue with database record creation
   - ❌ **Unsafe**: Delete file, return error to user

### Moderation Process

```python
# Example: Gig photo upload with moderation

# 1. Save file
file.save(file_path)

# 2. Moderate content
is_safe, message, details = moderate_image(file_path)

# 3. Log result
moderation_log = ContentModerationLog(
    user_id=user_id,
    image_type='gig_photo',
    image_path=file_path,
    is_safe=is_safe,
    violations=json.dumps(details['violations']),
    adult_likelihood=details['adult'],
    violence_likelihood=details['violence'],
    # ... other fields
)
db.session.add(moderation_log)
db.session.commit()

# 4. Handle unsafe content
if not is_safe:
    os.remove(file_path)  # Delete the file
    return jsonify({'error': message}), 400
```

## Monitoring & Administration

### View Moderation Logs

```sql
-- Recent rejections
SELECT user_id, image_type, violations, adult_likelihood, violence_likelihood, created_at
FROM content_moderation_log
WHERE is_safe = false
ORDER BY created_at DESC
LIMIT 50;

-- Rejection rate by image type
SELECT
    image_type,
    COUNT(*) as total_uploads,
    SUM(CASE WHEN is_safe = false THEN 1 ELSE 0 END) as rejections,
    ROUND(100.0 * SUM(CASE WHEN is_safe = false THEN 1 ELSE 0 END) / COUNT(*), 2) as rejection_rate
FROM content_moderation_log
GROUP BY image_type;

-- Violations breakdown
SELECT violations, COUNT(*) as count
FROM content_moderation_log
WHERE is_safe = false
GROUP BY violations
ORDER BY count DESC;

-- Users with most rejections
SELECT user_id, COUNT(*) as rejection_count
FROM content_moderation_log
WHERE is_safe = false
GROUP BY user_id
ORDER BY rejection_count DESC
LIMIT 20;
```

### API Response Examples

**Successful Upload:**
```json
{
  "message": "Reference photo uploaded successfully",
  "photo": {
    "id": 123,
    "filename": "abc123def456.jpg",
    "file_url": "/uploads/gig_photos/abc123def456.jpg"
  }
}
```

**Rejected Upload:**
```json
{
  "error": "Image rejected: Contains adult or sexually explicit content"
}
```

## Troubleshooting

### Common Issues

#### 1. Moderation Always Passes (Not Working)

**Symptoms**: All images upload successfully, even inappropriate ones

**Possible Causes**:
- Content moderation is disabled: Check `CONTENT_MODERATION_ENABLED=true`
- Credentials not found: Verify `GOOGLE_CLOUD_VISION_CREDENTIALS` path
- API not enabled: Enable Cloud Vision API in Google Cloud Console
- Quota exceeded: Check your Google Cloud quota

**Check logs**:
```bash
grep "Content moderation" /var/log/gighala/app.log
```

#### 2. All Images Being Rejected

**Symptoms**: Even safe images are rejected

**Possible Causes**:
- Thresholds too strict: Try `CONTENT_MODERATION_STRICT=false`
- API misconfiguration

**Solution**: Adjust thresholds in `.env`

#### 3. Google Cloud Vision API Errors

**Error**: `Failed to initialize Google Cloud Vision API`

**Solutions**:
1. Verify credentials file exists and is readable
2. Check credentials file has valid JSON
3. Ensure service account has Vision API permissions
4. Verify API is enabled in Google Cloud Console

#### 4. Database Migration Issues

**Error**: `relation "content_moderation_log" does not exist`

**Solution**: Run the migration script:
```bash
psql -U user -d database -f migrations/012_add_content_moderation.sql
```

## Security Considerations

1. **Credentials Security**:
   - Never commit Google Cloud credentials to git
   - Set restrictive file permissions (600)
   - Use environment variables for paths

2. **Fail-Safe Behavior**:
   - On API errors, system rejects images (fail closed)
   - Ensures safety even during service disruptions

3. **Audit Trail**:
   - All moderation attempts are logged
   - IP addresses tracked for abuse monitoring
   - Detailed violation information stored

4. **Privacy**:
   - Images sent to Google Cloud Vision API for analysis
   - Review Google's [data processing terms](https://cloud.google.com/vision/docs/data-usage)
   - Consider data residency requirements for your jurisdiction

## Cost Estimation

**Google Cloud Vision API Pricing** (as of 2025):
- First 1,000 units/month: Free
- 1,001 - 5,000,000 units: $1.50 per 1,000 units
- 5,000,001+ units: $0.60 per 1,000 units

**Example Monthly Costs**:
- 1,000 images/month: **Free**
- 10,000 images/month: ~$13.50
- 100,000 images/month: ~$148.50

**Note**: 1 SafeSearch detection = 1 unit

See [current pricing](https://cloud.google.com/vision/pricing) for details.

## Disabling Content Moderation

To temporarily disable content moderation:

```bash
# In .env file
CONTENT_MODERATION_ENABLED=false
```

Then restart the application. Images will upload without moderation checks.

**Warning**: Only disable in development or if you have alternative moderation in place.

## Support

For issues or questions:
1. Check application logs: `/var/log/gighala/app.log`
2. Review Google Cloud Console logs
3. Check database moderation logs
4. Contact your system administrator

## Future Enhancements

Potential improvements for future versions:
- [ ] Manual review queue for borderline cases
- [ ] User appeals process for false positives
- [ ] Alternative moderation providers (AWS Rekognition, Azure)
- [ ] OCR-based text moderation in images
- [ ] Custom ML model for context-specific moderation
- [ ] Batch processing for historical images
- [ ] Admin dashboard for moderation statistics
- [ ] Webhook notifications for admin on violations
