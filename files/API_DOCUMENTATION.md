# GigHalal API Documentation

Base URL: `https://your-app.up.railway.app/api`

## Authentication

### Register
**POST** `/api/register`

**Request Body:**
```json
{
  "username": "ahmad_zaki",
  "email": "ahmad@example.com",
  "password": "securepassword",
  "full_name": "Ahmad Zaki",
  "phone": "+60123456789",
  "location": "Kuala Lumpur",
  "user_type": "freelancer"
}
```

**Response:** `201 Created`
```json
{
  "message": "Registration successful",
  "user": {
    "id": 1,
    "username": "ahmad_zaki",
    "email": "ahmad@example.com",
    "user_type": "freelancer"
  }
}
```

### Login
**POST** `/api/login`

**Request Body:**
```json
{
  "email": "ahmad@example.com",
  "password": "securepassword"
}
```

**Response:** `200 OK`
```json
{
  "message": "Login successful",
  "user": {
    "id": 1,
    "username": "ahmad_zaki",
    "email": "ahmad@example.com",
    "user_type": "freelancer",
    "total_earnings": 2500.00,
    "rating": 4.8
  }
}
```

### Logout
**POST** `/api/logout`

**Response:** `200 OK`
```json
{
  "message": "Logged out successfully"
}
```

## Gigs

### Get All Gigs
**GET** `/api/gigs`

**Query Parameters:**
- `category` (optional): Filter by category ID
- `location` (optional): Filter by location
- `halal_only` (optional): true/false
- `search` (optional): Search in title and description

**Example:** `/api/gigs?category=design&location=Kuala Lumpur&halal_only=true`

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "title": "Design Logo for Halal Restaurant",
    "description": "Need a modern logo for my new halal restaurant...",
    "category": "design",
    "budget_min": 200,
    "budget_max": 500,
    "location": "Kuala Lumpur",
    "is_remote": true,
    "halal_compliant": true,
    "halal_verified": true,
    "is_instant_payout": true,
    "is_brand_partnership": false,
    "duration": "3-5 days",
    "views": 45,
    "applications": 8,
    "created_at": "2025-01-15T10:30:00Z"
  }
]
```

### Get Single Gig
**GET** `/api/gigs/:id`

**Response:** `200 OK`
```json
{
  "id": 1,
  "title": "Design Logo for Halal Restaurant",
  "description": "Need a modern logo...",
  "category": "design",
  "budget_min": 200,
  "budget_max": 500,
  "location": "Kuala Lumpur",
  "is_remote": true,
  "status": "open",
  "halal_compliant": true,
  "halal_verified": true,
  "duration": "3-5 days",
  "views": 45,
  "applications": 8,
  "created_at": "2025-01-15T10:30:00Z",
  "deadline": "2025-01-22T23:59:59Z",
  "client": {
    "id": 2,
    "username": "siti_restaurant",
    "rating": 4.9,
    "is_verified": true
  }
}
```

### Create Gig
**POST** `/api/gigs` (Requires Authentication)

**Request Body:**
```json
{
  "title": "Edit 5 Instagram Reels",
  "description": "Need professional video editing for social media content",
  "category": "video",
  "budget_min": 300,
  "budget_max": 600,
  "duration": "5-7 days",
  "location": "Remote",
  "is_remote": true,
  "halal_compliant": true,
  "is_instant_payout": false,
  "is_brand_partnership": true,
  "skills_required": ["Video Editing", "CapCut", "Social Media"],
  "deadline": "2025-02-01T23:59:59Z"
}
```

**Response:** `201 Created`
```json
{
  "message": "Gig created successfully",
  "gig_id": 15
}
```

### Apply to Gig
**POST** `/api/gigs/:id/apply` (Requires Authentication)

**Request Body:**
```json
{
  "cover_letter": "I have 5 years of experience in video editing...",
  "proposed_price": 450,
  "video_pitch": "https://example.com/video.mp4"
}
```

**Response:** `201 Created`
```json
{
  "message": "Application submitted successfully"
}
```

## Profile

### Get Profile
**GET** `/api/profile` (Requires Authentication)

**Response:** `200 OK`
```json
{
  "id": 1,
  "username": "ahmad_zaki",
  "email": "ahmad@example.com",
  "full_name": "Ahmad Zaki",
  "phone": "+60123456789",
  "user_type": "freelancer",
  "location": "Kuala Lumpur",
  "bio": "Experienced graphic designer...",
  "skills": ["Graphic Design", "Video Editing", "Canva"],
  "rating": 4.8,
  "total_earnings": 2500.00,
  "completed_gigs": 15,
  "is_verified": true,
  "halal_verified": true,
  "created_at": "2024-06-01T12:00:00Z"
}
```

### Update Profile
**PUT** `/api/profile` (Requires Authentication)

**Request Body:**
```json
{
  "full_name": "Ahmad Zaki bin Abdullah",
  "phone": "+60123456789",
  "location": "Shah Alam, Selangor",
  "bio": "Updated bio text...",
  "skills": ["Graphic Design", "Video Editing", "3D Animation"]
}
```

**Response:** `200 OK`
```json
{
  "message": "Profile updated successfully"
}
```

## Categories

### Get All Categories
**GET** `/api/categories`

**Response:** `200 OK`
```json
[
  {
    "id": "design",
    "name": "Graphic Design",
    "icon": "🎨"
  },
  {
    "id": "writing",
    "name": "Writing & Translation",
    "icon": "✍️"
  }
]
```

## Micro-Tasks

### Get Available Micro-Tasks
**GET** `/api/microtasks`

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "title": "Review Halal Restaurant on Google Maps",
    "description": "Visit and write honest review",
    "reward": 15.00,
    "task_type": "review"
  }
]
```

## Statistics

### Get Platform Statistics
**GET** `/api/stats`

**Response:** `200 OK`
```json
{
  "total_gigs": 2847,
  "active_gigs": 1523,
  "total_users": 50432,
  "total_earnings": 2345678.90
}
```

## Error Responses

### 400 Bad Request
```json
{
  "error": "Email already registered"
}
```

### 401 Unauthorized
```json
{
  "error": "Unauthorized"
}
```

### 404 Not Found
```json
{
  "error": "Gig not found"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error"
}
```

## Rate Limiting

- **Free Tier**: 100 requests/hour per IP
- **Authenticated**: 500 requests/hour per user
- **Premium**: 2000 requests/hour per user

## Webhooks (Coming Soon)

Subscribe to events:
- `gig.created`
- `gig.applied`
- `gig.completed`
- `payment.processed`

## Mobile App Integration

### React Native Example

```javascript
// API Client
const API_BASE_URL = 'https://your-app.up.railway.app/api';

const apiClient = {
  async login(email, password) {
    const response = await fetch(`${API_BASE_URL}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
      credentials: 'include' // Important for cookies
    });
    return response.json();
  },
  
  async getGigs(filters = {}) {
    const params = new URLSearchParams(filters);
    const response = await fetch(`${API_BASE_URL}/gigs?${params}`, {
      credentials: 'include'
    });
    return response.json();
  },
  
  async applyToGig(gigId, applicationData) {
    const response = await fetch(`${API_BASE_URL}/gigs/${gigId}/apply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(applicationData),
      credentials: 'include'
    });
    return response.json();
  }
};

export default apiClient;
```

### Flutter Example

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';

class ApiClient {
  static const String baseUrl = 'https://your-app.up.railway.app/api';
  
  Future<Map<String, dynamic>> login(String email, String password) async {
    final response = await http.post(
      Uri.parse('$baseUrl/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password}),
    );
    return jsonDecode(response.body);
  }
  
  Future<List<dynamic>> getGigs({Map<String, String>? filters}) async {
    var uri = Uri.parse('$baseUrl/gigs');
    if (filters != null) {
      uri = uri.replace(queryParameters: filters);
    }
    final response = await http.get(uri);
    return jsonDecode(response.body);
  }
}
```

## WebSocket Support (Future)

Real-time features planned:
- Live gig notifications
- Chat between freelancer and client
- Real-time application status updates

## Best Practices

1. **Always use HTTPS** in production
2. **Store tokens securely** in mobile app
3. **Implement retry logic** for failed requests
4. **Cache API responses** when appropriate
5. **Handle offline scenarios** gracefully
6. **Respect rate limits** 
7. **Validate inputs** on client-side before API calls
8. **Use pagination** for large data sets

## Support

For API support:
- Email: api@gighalal.com
- Documentation: https://docs.gighalal.com
- Status Page: https://status.gighalal.com
