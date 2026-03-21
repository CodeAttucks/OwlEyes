cd api
pip install -r requirements.txt

web: uvicorn main:app --host 0.0.0.0 --port $PORT

railway init
railway up

DATABASE_URL=your_supabase_connection

cd web
npm install
vercel deploy

NEXT_PUBLIC_MAPBOX_TOKEN=your_token
NEXT_PUBLIC_API_URL=https://your-railway-url