# Docker Health

Check Docker services health and verify full pipeline.

## Instructions

1. **Check services**: `docker compose ps`
2. **Verify health checks**: All services should show "healthy"
3. **Test API**: `curl -s http://localhost:8080/api/v1/health`
4. **Test UI**: `curl -s http://localhost:3000 | head -5`
5. **Report**: Service status table + any issues found

If "restart" is requested:
```
docker compose down
docker compose up -d --build
# Wait for health checks
sleep 30
docker compose ps
```

If "logs <service>" is requested:
```
docker compose logs --tail=50 <service>
```

## Arguments
- `$ARGUMENTS` — optional: "restart" to rebuild, "logs <service>" to show logs
