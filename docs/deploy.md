# Deployment

This service is a standard FastAPI app and can be deployed as a container or a
Python process. For local development, see ../README.md.

## Production Environment Variables

Required:
- `DATABASE_URL` (e.g. `postgresql+psycopg://user:pass@host:5432/chat_archive`)

Optional:
- Logging context headers are accepted on every request: `X-Request-ID`, `X-Client-ID`

## Container Deployment

1. Build an image:
   ```bash
   docker build -t chat-archive .
   ```
2. Run the container:
   ```bash
   docker run \
     -e DATABASE_URL="postgresql+psycopg://user:pass@host:5432/chat_archive" \
     -p 8000:8000 \
     chat-archive
   ```

## Migrations

Run migrations against the target database before serving traffic:
```bash
make migrate
```

In containerized environments, you can run migrations in a one-off task using
the same image and `DATABASE_URL`.

## Health Checks

Use the health endpoint for liveness probes:
- `GET /health`

## Reverse Proxy / TLS

If you put the app behind a reverse proxy (NGINX, ALB, etc.), ensure:
- `X-Request-ID` and `X-Client-ID` headers are forwarded if you use them.
- Timeouts are sufficient for expected query durations.

## Scaling Notes

- The app is stateless and can be horizontally scaled.
- Database performance and indexing are the primary throughput constraints.
- For heavy query loads, consider read replicas and connection pooling.
