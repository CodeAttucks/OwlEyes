# BEAD Platform - Broadband Infrastructure Planning & Monitoring

A full-stack application for managing BEAD (Broadband Equity and Deployment) projects, fiber deployment, and infrastructure analytics.

## 🎯 About

The BEAD Platform provides comprehensive tools for:
- **Project Management** - Track broadband infrastructure projects across states
- **Fiber Route Planning** - Visualize and manage fiber optic deployments
- **Service Location Mapping** - Monitor coverage and served locations using GIS
- **Financial Tracking** - Track expenditures and calculate cost efficiency
- **Analytics & Reporting** - Generate insights and export reports
- **Multi-tenant Support** - Secure, role-based access for organizations

## 📁 Project Structure

```
bead-platform/
├── api/                      # FastAPI backend
│   ├── main.py              # App entry point
│   ├── db.py                # Database connection
│   ├── routers/             # API route handlers
│   │   ├── projects.py
│   │   ├── fiber.py
│   │   ├── reports.py
│   │   └── uploads.py
│   ├── services/            # Business logic
│   │   ├── ai_insights.py
│   │   ├── etl_service.py
│   │   └── bead_report.py
│   └── requirements.txt
├── web/                      # Next.js frontend
│   ├── app/                 # Pages
│   │   ├── dashboard/
│   │   ├── reports/
│   │   └── projects/
│   ├── components/          # Reusable components
│   │   ├── KPI.tsx
│   │   └── Insights.tsx
│   ├── lib/                 # Utilities
│   │   └── api.ts
│   └── styles/
├── db/                       # Database schemas
│   ├── schema.sql           # 56-table enterprise schema
│   ├── rls.sql              # Row-level security policies
│   ├── seed.sql             # Sample data
│   └── views.sql            # Database views
├── etl/                      # Data pipeline
│   ├── fcc_fabric_loader.py
│   └── bdc_loader.py
├── scripts/                  # Utility scripts
└── .env.example             # Environment template
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+** - Backend runtime
- **Node.js 16+** - Frontend build
- **PostgreSQL 15+** with PostGIS - Spatial database
- **Docker** (optional) - For containerized database

### Installation

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd bead-platform
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env.local
   ```
   
   Edit `.env.local` with your configuration:
   ```env
   # Database
   DATABASE_URL=postgresql://postgres:password@localhost:5432/bead_platform
   
   # Frontend
   NEXT_PUBLIC_API_URL=http://localhost:8000
   NEXT_PUBLIC_MAPBOX_TOKEN=your_mapbox_token
   NEXT_PUBLIC_POWERBI_EMBED_URL=https://app.powerbi.com/view?r=YOUR_EMBED_URL
   ```

3. **Start the PostgreSQL database** (Docker)
   ```bash
   docker run --name bead-db \
     -e POSTGRES_PASSWORD=password \
     -e POSTGRES_DB=bead_platform \
     -p 5432:5432 \
     -d postgis/postgis:15-3.4
   ```

4. **Initialize the database**
   ```bash
   docker exec bead-db psql -U postgres -d bead_platform -f /tmp/schema.sql
   docker exec bead-db psql -U postgres -d bead_platform -f /tmp/rls.sql
   docker exec bead-db psql -U postgres -d bead_platform -f /tmp/seed.sql
   ```

### Running Locally

**Backend (FastAPI)**
```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend (Next.js)**
```bash
cd web
npm install
npm run dev
```

The application will be available at:
- Frontend: `http://localhost:3000`
- API: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`

## 📊 Key Features

### Dashboard (`/dashboard`)
- **KPI Cards** - Real-time metrics on projects, locations, and fiber miles
- **Project Overview** - Table of all projects with status indicators
- **Fiber Route Analytics** - Statistics and coverage analysis

### Reports (`/reports`)
- **Power BI Integration** - Embedded dashboards for visualization
- **Export Functionality** - Download data as Excel files
- **AI Insights** - Automated analysis with recommendations

### API Endpoints

**Projects**
```
GET  /api/projects          # List all projects
POST /api/projects          # Create project
GET  /api/projects/{id}     # Get project details
```

**Fiber Routes**
```
GET  /api/fiber              # List all fiber routes
GET  /api/fiber/{project_id} # Get fiber for project
POST /api/fiber              # Create fiber route
GET  /api/fiber/stats/summary # Fiber statistics
```

**Reports & Analytics**
```
GET  /api/reports            # List reports
GET  /api/reports/export     # Export data (Excel)
GET  /api/reports/insights   # AI-driven insights
GET  /api/reports/summary    # Executive summary
```

**File Upload**
```
POST /api/upload             # Upload CSV/shapefile
```

## 🏗️ Database Schema

The platform uses a 56-table enterprise schema including:

**Core Tables:**
- `organizations` - Multi-tenant support
- `projects` - BEAD projects and initiatives
- `fiber_routes` - GIS-enabled fiber deployment
- `service_locations` - Coverage points with coordinates

**Financial Tables:**
- `expenditures` - Budget tracking
- `budget_allocations` - Financial planning

**GIS Tables:**
- Spatial tables with PostGIS geometry support
- GIST indexes for geographic queries
- Row-level security for data isolation

## 🔒 Security

- **Row-Level Security** - Multi-tenant data isolation at database level
- **Environment Variables** - Sensitive config in `.env.local`
- **Input Validation** - FastAPI request validation
- **CORS Configuration** - Restricted API access

## 📈 Performance Features

- **Spatial Indexing** - Fast geographic queries
- **Connection Pooling** - Efficient database usage
- **Caching** - React Query for frontend data management
- **Pagination** - Large dataset handling

## 🛠️ Development

### Making Changes

1. **Backend changes** - Edit files in `api/` and restart server
2. **Frontend changes** - Edit files in `web/app/` and refresh browser
3. **Database schema** - Modify SQL files and re-run migrations

### Adding Features

**New API endpoint:**
```python
# api/routers/new_feature.py
from fastapi import APIRouter
router = APIRouter(prefix="/feature")

@router.get("/")
def get_feature():
    return {"data": []}
```

Then include in `api/main.py`:
```python
app.include_router(new_feature.router)
```

**New component:**
```tsx
// web/components/NewComponent.tsx
export default function NewComponent() {
  return <div>Component</div>
}
```

## 🌍 Deployment

### Option 1: Railway + Vercel

**Backend (Railway):**
```bash
railway init
railway up
```

**Frontend (Vercel):**
```bash
cd web
vercel deploy
```

### Option 2: Docker Compose

```bash
docker-compose up -d
```

### Environment Variables for Production

```env
DATABASE_URL=postgresql://user:password@db-host:5432/bead
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_MAPBOX_TOKEN=pk_...
NEXT_PUBLIC_POWERBI_EMBED_URL=https://app.powerbi.com/view?r=...
```

## 📚 API Documentation

Once the backend is running, view interactive docs at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🧪 Testing

```bash
# Backend tests
cd api
pytest

# Frontend tests
cd web
npm test
```

## 📦 Dependencies

**Backend:**
- FastAPI - Web framework
- psycopg2 - PostgreSQL driver
- GeoAlchemy2 - Spatial support
- Pandas - Data processing
- SQLAlchemy - ORM

**Frontend:**
- Next.js - React framework
- Tailwind CSS - Styling
- Heroicons - Icons
- TypeScript - Type safety

## 🤝 Contributing

1. Create a feature branch
2. Make changes with clear commit messages
3. Push to repository
4. Create Pull Request with description

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check documentation at `/docs`
- Review API docs at `http://localhost:8000/docs`

## 📄 License

[Your License Here]

## 🎓 Learning Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [PostGIS Documentation](https://postgis.net/documentation/)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)

---

**Happy building! 🚀**