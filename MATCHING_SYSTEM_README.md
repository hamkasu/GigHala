# GigHala AI-Powered Worker-Gig Matching System

## Overview

The AI-powered matching system intelligently connects workers with relevant gig opportunities based on skills, location, category specialization, budget compatibility, and other factors. Instead of sending all new gigs to all workers, the system analyzes each worker's profile and only sends highly relevant opportunities.

## How It Works

### Matching Algorithm

The system uses a weighted scoring algorithm that considers multiple factors:

1. **Skill Match (40%)** - Most important factor
   - Compares worker's skills with gig requirements
   - Uses Jaccard similarity and coverage metrics
   - Prioritizes workers who have the required skills

2. **Category Match (25%)**
   - Checks if worker specializes in the gig's category
   - Workers with matching specializations score higher

3. **Location Match (20%)**
   - Calculates distance between worker and gig location
   - Remote gigs always score perfectly
   - Closer workers score higher for on-site gigs

4. **Budget Compatibility (10%)**
   - Compares gig budget with worker's earnings history
   - Ensures gigs match worker's experience level

5. **Freshness (5%)**
   - Newer gigs receive slightly higher scores
   - Encourages quick applications

### Minimum Threshold

- Workers only receive gigs with **30% or higher match score**
- Maximum of **10 gigs per email** to avoid overwhelming workers
- Emails are personalized showing match percentage and matched skills

## Features

### For Workers

- **Personalized Recommendations**: Only receive gigs that match your skills and preferences
- **Match Explanation**: See why each gig matches you (matched skills, location, category)
- **Match Percentage**: Visual indicator showing how well each gig fits your profile
- **Smart Filtering**: Automatic filtering based on location, skills, and specializations

### For Platform

- **Higher Application Quality**: Workers apply to more relevant gigs
- **Reduced Email Fatigue**: Workers receive fewer but better-matched opportunities
- **Better Engagement**: Personalized emails have higher open and click-through rates
- **AI-Driven Insights**: Track which factors lead to successful matches

## Schedule

The matching system runs **twice daily**:

- **9:00 AM** (Malaysia Time) - Morning digest
- **9:00 PM** (Malaysia Time) - Evening digest

*Note: Runs 1 hour after the general gig digest (8 AM / 8 PM)*

## Email Template

Workers receive a beautifully designed email showing:

- Match percentage badge (e.g., "85% Match")
- Why the gig matches them
- Matched skills highlighted
- Gig details (title, budget, location, category)
- Direct "View Details & Apply" button

## Files

### Core Matching Engine

**`gig_matching_service.py`**
- Main matching algorithm
- Scoring functions for each factor
- Worker-to-gig and gig-to-worker matching

Key methods:
- `find_matching_gigs_for_worker()` - Find gigs for a specific worker
- `find_workers_for_gig()` - Find workers for a specific gig
- `get_all_worker_matches()` - Get matches for all workers (used by scheduler)
- `calculate_match_score()` - Calculate overall match score

### Scheduled Jobs

**`scheduled_jobs.py`**
- Contains `send_matched_gigs_email()` function
- Integrates with APScheduler
- Handles email sending and logging

### Email Template

**`templates/email_matched_gigs.html`**
- Responsive HTML email template
- Shows match percentage and explanation
- Highlights matched skills

## Testing

### Interactive Test Script

Run the test script to manually test the matching system:

```bash
python test_matching.py
```

This launches an interactive menu where you can:
1. Test matching for a specific worker
2. Test matching for all workers
3. Test finding workers for a specific gig

### Command Line Usage

```bash
# Test matching for worker ID 1 (last 24 hours)
python test_matching.py worker 1

# Test matching for worker ID 1 (last 48 hours)
python test_matching.py worker 1 48

# Test all workers (show top 10)
python test_matching.py all 24 10

# Find matching workers for gig ID 5
python test_matching.py gig 5
```

## Configuration

### Matching Weights

You can adjust the importance of each factor in `gig_matching_service.py`:

```python
# Matching weights for scoring algorithm
self.WEIGHT_SKILLS = 0.40      # 40% - Skills match
self.WEIGHT_CATEGORY = 0.25    # 25% - Category specialization
self.WEIGHT_LOCATION = 0.20    # 20% - Distance/proximity
self.WEIGHT_BUDGET = 0.10      # 10% - Budget compatibility
self.WEIGHT_FRESHNESS = 0.05   # 5% - Gig freshness
```

### Thresholds

```python
self.MIN_MATCH_SCORE = 0.3     # Only send gigs with >30% match
self.MAX_DISTANCE_KM = 50      # Max distance for on-site gigs
self.MAX_GIGS_PER_EMAIL = 10   # Limit gigs per notification
```

### Schedule Times

Update the schedule in `scheduled_jobs.py`:

```python
# Morning digest at 9 AM
scheduler.add_job(
    func=lambda: send_matched_gigs_email(...),
    trigger=CronTrigger(hour=9, minute=0, timezone=timezone),
    id='matched_gigs_morning',
    name='Send AI-matched gigs email (9 AM)',
    replace_existing=True
)
```

## Database

The system uses existing database tables:

- **User** - Worker profiles, skills, location
- **Gig** - Gig postings, requirements, location
- **WorkerSpecialization** - Worker category specializations
- **NotificationPreference** - Email notification settings
- **EmailDigestLog** - Tracks digest sends (uses `digest_type='matched_gigs'`)

## API Integration (Future)

The matching service can be used for real-time features:

```python
from gig_matching_service import GigMatchingService

# Initialize
matching_service = GigMatchingService(db, User, Gig, WorkerSpecialization, calculate_distance)

# Get matches for a worker
matches = matching_service.find_matching_gigs_for_worker(user, hours_back=72)

# Get match score for worker-gig pair
score, breakdown = matching_service.calculate_match_score(worker, gig)

# Find qualified workers for a gig
workers = matching_service.find_workers_for_gig(gig, min_score=0.5)
```

### Potential Uses

- **Instant Notifications**: Notify workers immediately when a highly-matched gig is posted
- **Gig Recommendations Page**: Show personalized gig feed on dashboard
- **Smart Search Results**: Rank search results by match score
- **Worker Suggestions**: Show clients the best-matched workers for their gigs
- **Analytics Dashboard**: Track match quality and application rates

## Performance Considerations

- **Database Queries**: Optimized to minimize queries per worker
- **JSON Parsing**: Skills are cached during matching to avoid repeated parsing
- **Batch Processing**: All workers are processed in a single scheduled job
- **Email Throttling**: Emails sent individually with error handling

## Monitoring

Check the `EmailDigestLog` table for matching job results:

```python
# Get latest matching job result
last_job = EmailDigestLog.query.filter_by(
    digest_type='matched_gigs'
).order_by(EmailDigestLog.sent_at.desc()).first()

print(f"Sent: {last_job.sent_at}")
print(f"Recipients: {last_job.recipient_count}")
print(f"Gigs sent: {last_job.gig_count}")
print(f"Success: {last_job.success}")
```

## Troubleshooting

### No Matches Found

**Possible reasons:**
1. No new gigs in the time window
2. Workers don't have skills in their profiles
3. Minimum match score too high (adjust threshold)
4. Workers have disabled email notifications

**Solutions:**
- Run test script to diagnose: `python test_matching.py worker <id>`
- Check if workers have skills and specializations set
- Verify gigs have `skills_required` field populated
- Lower `MIN_MATCH_SCORE` threshold for testing

### Emails Not Sending

**Check:**
1. Brevo API key is configured in `.env`
2. Users have valid email addresses
3. `NotificationPreference.email_new_gig` is True
4. Check `EmailDigestLog` for error messages

### Poor Match Quality

**Improve by:**
1. Encourage workers to complete their profiles (skills, specializations)
2. Ensure gigs have detailed `skills_required`
3. Add location coordinates for better distance matching
4. Adjust matching weights for your use case

## Future Enhancements

- **Machine Learning**: Train model on successful applications
- **Collaborative Filtering**: "Workers who applied to X also applied to Y"
- **Worker Preferences**: Let workers set preferred categories and budget ranges
- **Dynamic Weights**: Adjust weights based on worker's application history
- **A/B Testing**: Test different matching algorithms
- **Smart Timing**: Send emails at optimal times based on worker engagement
- **Push Notifications**: Real-time push for high-match gigs
- **Match Feedback**: Let workers rate match quality to improve algorithm

## Support

For questions or issues with the matching system:

1. Check this README
2. Run the test script for diagnostics
3. Review the logs in `EmailDigestLog` table
4. Contact the development team

---

**Built with ❤️ for GigHala**
