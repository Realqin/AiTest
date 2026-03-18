# AiTest

Lightweight frontend-backend project based on FastAPI and React.

## Structure

```txt
AiTest/
  backend/
    app/
      api/
      core/
      store/
      main.py
    requirements.txt
    .env.example
  frontend/
    src/
    package.json
```

## Start Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

- Health: `http://localhost:8001/health`
- Swagger: `http://localhost:8001/swagger`

## Start Frontend

```bash
cd frontend
npm install
npm run dev
```

- URL: `http://localhost:5174`

## Notes

- Backend storage has been switched to MySQL.
- Configure the connection in `backend/.env` with `AITEST_DATABASE_URL`.
- Use `backend/.env.example` as a template.
- Create the MySQL database `aitest` before starting the backend.
