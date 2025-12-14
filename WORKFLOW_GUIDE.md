# GigHala Complete Workflow Guide
## Client to Worker End-to-End Process

This document outlines the complete workflow from when a client posts a gig to when a worker completes it.

---

## 📋 Workflow Overview

```
1. Client posts gig (status: 'open')
2. Freelancers apply to gig
3. Client views applicants
4. Client accepts one freelancer (status: 'in_progress', others rejected)
5. Freelancer uploads work photos
6. Freelancer submits work (status: 'pending_review')
7. Client reviews work photos
8. Client either:
   a) Approves work (status: 'completed') → Payment & Reviews
   b) Requests revisions (status: 'in_progress') → Back to step 5
9. Both parties leave reviews
```

---

## 🔄 Detailed Workflow Steps

### **STEP 1: Client Posts a Gig**

**API Endpoint:** `POST /api/gigs`

**Request:**
```javascript
{
  "title": "Design Logo for Halal Restaurant",
  "description": "Need a modern logo...",
  "category": "design",
  "budget_min": 200,
  "budget_max": 500,
  "duration": "3-5 days",
  "location": "Kuala Lumpur",
  "is_remote": true,
  "halal_compliant": true,
  "deadline": "2025-12-30T00:00:00"
}
```

**Gig Status:** `open`

---

### **STEP 2: Freelancers Apply to Gig**

**API Endpoint:** `POST /api/gigs/{gig_id}/apply`

**Request:**
```javascript
{
  "cover_letter": "I have 5 years of experience in logo design...",
  "proposed_price": 350,
  "video_pitch": "https://youtube.com/..."
}
```

**Application Status:** `pending`

Multiple freelancers can apply to the same gig.

---

### **STEP 3: Client Views Applicants**

**API Endpoint:** `GET /api/gigs/{gig_id}/applications`

**Response:**
```javascript
{
  "gig_id": 123,
  "total_applications": 5,
  "applications": [
    {
      "id": 456,
      "freelancer": {
        "id": 10,
        "username": "ahmad_designer",
        "full_name": "Ahmad Zaki",
        "rating": 4.8,
        "review_count": 25,
        "completed_gigs": 30,
        "bio": "Professional graphic designer...",
        "location": "Kuala Lumpur",
        "skills": ["Photoshop", "Illustrator"],
        "is_verified": true,
        "halal_verified": true
      },
      "cover_letter": "I have 5 years of experience...",
      "proposed_price": 350,
      "video_pitch": "https://youtube.com/...",
      "status": "pending",
      "created_at": "2025-12-14T10:30:00"
    }
    // ... more applications
  ]
}
```

---

### **STEP 4: Client Accepts One Freelancer**

**API Endpoint:** `POST /api/applications/{application_id}/accept`

**What Happens:**
- ✅ Selected application status → `accepted`
- ✅ Gig status → `in_progress`
- ✅ Gig.freelancer_id is set
- ❌ All other pending applications → `rejected`

**Response:**
```javascript
{
  "message": "Application accepted successfully",
  "gig": {
    "id": 123,
    "status": "in_progress",
    "freelancer_id": 10
  }
}
```

**Alternative:** Client can also reject applications individually:

**API Endpoint:** `POST /api/applications/{application_id}/reject`

---

### **STEP 5: Freelancer Uploads Work Photos**

**API Endpoint:** `POST /api/gigs/{gig_id}/work-photos`

**Request (multipart/form-data):**
```javascript
photo: [File]
caption: "Logo design - Initial concept"
upload_stage: "work_in_progress"  // or "completed" or "revision"
```

**Response:**
```javascript
{
  "message": "Photo uploaded successfully",
  "photo": {
    "id": 789,
    "gig_id": 123,
    "uploader_id": 10,
    "uploader_type": "freelancer",
    "filename": "a1b2c3d4e5f6.png",
    "original_filename": "logo_design.png",
    "file_url": "/uploads/work_photos/a1b2c3d4e5f6.png",
    "file_size": 245678,
    "caption": "Logo design - Initial concept",
    "upload_stage": "work_in_progress",
    "created_at": "2025-12-14T15:20:00"
  }
}
```

Freelancer can upload multiple photos.

---

### **STEP 6: Freelancer Submits Work**

**API Endpoint:** `POST /api/gigs/{gig_id}/submit-work`

**What Happens:**
- ✅ Validates at least 1 work photo uploaded
- ✅ Application.work_submitted → `true`
- ✅ Application.work_submission_date → current timestamp
- ✅ Gig status → `pending_review`

**Response:**
```javascript
{
  "message": "Work submitted successfully. Waiting for client review.",
  "gig": {
    "id": 123,
    "status": "pending_review",
    "work_photos_count": 3
  }
}
```

---

### **STEP 7: Client Views Work Photos**

**API Endpoint:** `GET /api/gigs/{gig_id}/work-photos`

**Response:**
```javascript
{
  "gig_id": 123,
  "total_photos": 3,
  "photos": [
    {
      "id": 789,
      "uploader_type": "freelancer",
      "file_url": "/uploads/work_photos/a1b2c3d4e5f6.png",
      "caption": "Final logo design",
      "upload_stage": "completed",
      "created_at": "2025-12-14T16:45:00"
    }
    // ... more photos
  ]
}
```

Client can view each photo at: `GET /uploads/work_photos/{filename}`

---

### **STEP 8a: Client Approves Work** ✅

**API Endpoint:** `POST /api/gigs/{gig_id}/approve-work`

**What Happens:**
- ✅ Gig status → `completed`
- ✅ Freelancer.completed_gigs += 1
- ✅ Payment can now be processed
- ✅ Both parties can leave reviews

**Response:**
```javascript
{
  "message": "Work approved! Gig marked as completed.",
  "gig": {
    "id": 123,
    "status": "completed"
  }
}
```

**Next Steps:** Both client and freelancer can leave reviews.

---

### **STEP 8b: Client Requests Revisions** 🔄

**API Endpoint:** `POST /api/gigs/{gig_id}/request-revision`

**Request:**
```javascript
{
  "notes": "Please make the logo text bigger and change the color to green"
}
```

**What Happens:**
- ✅ Gig status → `in_progress` (back to step 5)
- ✅ Application.work_submitted → `false`
- ✅ Application.work_submission_date → `null`
- ✅ Freelancer is notified to make revisions

**Response:**
```javascript
{
  "message": "Revision requested. Freelancer has been notified.",
  "gig": {
    "id": 123,
    "status": "in_progress"
  },
  "revision_notes": "Please make the logo text bigger..."
}
```

Freelancer goes back to **STEP 5** to upload revised photos.

---

### **STEP 9: Leave Reviews** (After completion)

**API Endpoint:** `POST /api/gigs/{gig_id}/reviews`

**Request (Client reviewing Freelancer):**
```javascript
{
  "rating": 5,
  "comment": "Excellent work! Very professional and delivered on time."
}
```

**Request (Freelancer reviewing Client):**
```javascript
{
  "rating": 5,
  "comment": "Great client, clear requirements and quick payment."
}
```

Both parties can leave one review per gig.

---

## 🚫 Cancel Gig (Optional)

**API Endpoint:** `POST /api/gigs/{gig_id}/cancel`

**Request:**
```javascript
{
  "reason": "No longer needed"
}
```

**Restrictions:**
- ✅ Only client can cancel
- ❌ Cannot cancel completed gigs
- ✅ Can cancel: `open`, `in_progress`, `pending_review`

**What Happens:**
- ✅ Gig status → `cancelled`

---

## 📊 Gig Status Flow Chart

```
┌──────┐
│ OPEN │ ← Client posts gig
└──┬───┘
   │
   │ Client accepts freelancer
   ▼
┌───────────────┐
│ IN_PROGRESS   │ ← Freelancer works on gig
└──────┬────────┘
       │
       │ Freelancer submits work
       ▼
┌────────────────┐
│ PENDING_REVIEW │ ← Client reviews work
└────┬──────┬────┘
     │      │
     │      │ Client requests revisions
     │      └──────────────────────┐
     │                             │
     │ Client approves             ▼
     ▼                      Back to IN_PROGRESS
┌───────────┐
│ COMPLETED │ ← Payment & Reviews
└───────────┘

(CANCELLED can happen from OPEN, IN_PROGRESS, or PENDING_REVIEW)
```

---

## 🎯 Application Status Flow

```
┌─────────┐
│ PENDING │ ← Freelancer applies
└────┬────┘
     │
     ├─► Client accepts ──► ACCEPTED
     │
     └─► Client rejects ──► REJECTED
```

---

## 📸 Work Photo Upload Stages

1. **work_in_progress** - Freelancer is still working
2. **revision** - After client requested changes
3. **completed** - Freelancer considers it final

These are informational and help both parties track progress.

---

## 🔐 Authorization Rules

| Action | Who Can Do It | When |
|--------|---------------|------|
| Post gig | Client | Anytime |
| Apply to gig | Freelancer | Gig status = `open` |
| View applications | Client (gig owner) | Anytime |
| Accept/Reject application | Client (gig owner) | Gig status = `open` |
| Upload work photos | Assigned freelancer OR client | Gig status = `in_progress` or `pending_review` |
| View work photos | Freelancer, Client, Admin | Anytime after upload |
| Submit work | Assigned freelancer | Gig status = `in_progress`, must have ≥1 photo |
| Approve work | Client (gig owner) | Gig status = `pending_review` |
| Request revision | Client (gig owner) | Gig status = `pending_review` |
| Cancel gig | Client (gig owner) | Gig status ≠ `completed` |
| Leave review | Client or Freelancer | Gig status = `completed` |

---

## 💡 Usage Examples

### Frontend Implementation Example (React/JavaScript)

```javascript
// Client views applicants
const viewApplicants = async (gigId) => {
  const response = await fetch(`/api/gigs/${gigId}/applications`, {
    credentials: 'include'
  });
  const data = await response.json();

  // Display applicants with their profiles, ratings, etc.
  data.applications.forEach(app => {
    console.log(`${app.freelancer.full_name} - Rating: ${app.freelancer.rating}`);
  });
};

// Client accepts freelancer
const acceptFreelancer = async (applicationId) => {
  const response = await fetch(`/api/applications/${applicationId}/accept`, {
    method: 'POST',
    credentials: 'include'
  });
  const data = await response.json();
  alert(data.message); // "Application accepted successfully"
};

// Freelancer uploads work photo
const uploadWorkPhoto = async (gigId, file, caption) => {
  const formData = new FormData();
  formData.append('photo', file);
  formData.append('caption', caption);
  formData.append('upload_stage', 'completed');

  const response = await fetch(`/api/gigs/${gigId}/work-photos`, {
    method: 'POST',
    body: formData,
    credentials: 'include'
  });
  const data = await response.json();
  return data.photo; // Photo details
};

// Freelancer submits work
const submitWork = async (gigId) => {
  const response = await fetch(`/api/gigs/${gigId}/submit-work`, {
    method: 'POST',
    credentials: 'include'
  });
  const data = await response.json();
  alert(data.message); // "Work submitted successfully..."
};

// Client approves work
const approveWork = async (gigId) => {
  const response = await fetch(`/api/gigs/${gigId}/approve-work`, {
    method: 'POST',
    credentials: 'include'
  });
  const data = await response.json();
  alert(data.message); // "Work approved! Gig marked as completed."
};

// Client requests revision
const requestRevision = async (gigId, notes) => {
  const response = await fetch(`/api/gigs/${gigId}/request-revision`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ notes }),
    credentials: 'include'
  });
  const data = await response.json();
  alert(data.message); // "Revision requested..."
};
```

---

## ⚠️ Error Handling

All endpoints return appropriate HTTP status codes:

- **200** - Success
- **201** - Created (for uploads)
- **400** - Bad request (validation errors)
- **401** - Unauthorized (not logged in)
- **403** - Forbidden (wrong user role)
- **404** - Not found
- **500** - Server error

Always check for errors:

```javascript
const response = await fetch('/api/gigs/123/submit-work', {
  method: 'POST',
  credentials: 'include'
});

if (!response.ok) {
  const error = await response.json();
  alert(error.error); // Display error message
}
```

---

## 🗄️ Database Updates

The workflow uses these main tables:

1. **gig** - Tracks gig status
2. **application** - Tracks applications and work submission
3. **work_photo** - Stores uploaded work photos
4. **user** - Updated when gig completes (completed_gigs++)

No additional migrations needed beyond what's already in `work_photo_migration_postgresql.sql`!

---

## 🎉 Summary

This complete workflow ensures:
- ✅ Clear communication between client and freelancer
- ✅ Structured application and selection process
- ✅ Photo evidence of work completion
- ✅ Client approval before payment
- ✅ Revision system for quality control
- ✅ Proper authorization at every step

**Start using it today! All endpoints are ready in both `app.py` and `files/app.py`.**
