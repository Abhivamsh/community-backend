# Threadly — Community Feed with Karma Leaderboard

## Design Goal
Build a performant discussion platform that supports deeply nested conversations while ensuring accurate, real-time karma aggregation through a transactional data model.

---

## Project Overview

Threadly is a community discussion platform where users can create posts, participate in threaded conversations, and earn karma through community engagement.

The system is designed to prioritize **data correctness, query efficiency, and concurrency safety**, ensuring that leaderboard rankings are dynamically calculated from transactional history rather than stored aggregates.

---

## Live Demo

**Frontend:**  
👉 https://thecommuntity.vercel.app  

**Backend API Base:**   
👉 https://communitybackend-6wui.onrender.com 

**Example Endpoint:**  
👉 https://communitybackend-6wui.onrender.com/api/posts/

---

## Tech Stack

**Backend**
- Django  
- Django REST Framework  
- PostgreSQL  

**Frontend**
- React  
- Tailwind CSS  

**Deployment**
- Render (Backend)
- Vercel (Frontend)

---

## Core Features

✅ Community feed displaying posts with author and like count  
✅ Threaded nested comments (Reddit-style discussions)  
✅ Transaction-based karma system  
✅ Top contributors leaderboard based on karma earned in the last 24 hours  
✅ Database-level protection against double likes  
✅ Optimized ORM queries to prevent N+1 problems  
✅ Fully deployed with production-ready routing  

---

## Architecture Decision

Karma is stored as **transactional history** rather than a derived total on the User model.  
This ensures:

- Accurate time-window aggregation  
- No stale leaderboard values  
- Better auditability  
- Safer concurrent updates  

The leaderboard is dynamically computed using database aggregation queries.

---

## How to Run Locally

### Backend

```bash
git clone https://github.com/Abhivamsh/community-backend.git
cd community-backend

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/posts/` | GET | List all posts |
| `/api/posts/` | POST | Create a new post |
| `/api/posts/{id}/` | GET | Get post with comments |
| `/api/posts/{id}/like/` | POST | Like a post (+5 karma to author) |
| `/api/comments/` | POST | Create a comment |
| `/api/comments/{id}/like/` | POST | Like a comment (+1 karma to author) |
| `/api/leaderboard/` | GET | Top 5 users by karma (last 24h) |

---

## Karma System

| Action | Karma Awarded |
|--------|---------------|
| Like on Post | +5 to post author |
| Like on Comment | +1 to comment author |

---

## Database Models

- **Post** — Content with author reference
- **Comment** — Threaded comments with parent reference
- **Like** — Tracks likes with DB-level duplicate prevention
- **KarmaTransaction** — Audit log for karma changes

---

## License

MIT
