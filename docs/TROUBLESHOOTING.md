# Troubleshooting Guide

## Common Issues

### Port Already in Use

**Problem:** Address already in use error

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

### API Key Error

**Problem:** CLAUDE_API_KEY not found

**Solution:**
1. Create `backend/.env` file
2. Add: `CLAUDE_API_KEY=sk-ant-...`
3. Restart backend

### Frontend Can't Connect to Backend

**Problem:** CORS or network error

**Solution:**
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check proxy in `frontend/vite.config.js`
3. Update API URL if running remotely

### Database Issues

**Problem:** SQLite database errors

**Solution:**
```bash
# Remove database
rm backend/pc_assistant.db

# Restart backend to recreate
```

### Dependencies Not Installing

**Problem:** pip install fails

**Solution:**
```bash
# Upgrade pip
pip install --upgrade pip

# Clear cache
pip install -r requirements.txt --no-cache-dir
```

## Performance Issues

### High CPU Usage

- Check running processes: `GET /api/system/processes`
- Stop unnecessary services
- Restart application

### Memory Leaks

- Monitor with: `GET /api/system/info` (repeated calls)
- Check long-running conversations
- Restart backend if needed

## Getting Help

Check logs for detailed error messages:
- Backend: stdout from uvicorn
- Frontend: browser developer console
- System: application event logs
