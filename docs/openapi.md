# OpenAPI and Docs

For quickstart and local development, see ../README.md.

## Endpoints

When the service is running, the OpenAPI and documentation endpoints are:
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Exporting the Spec

To save the spec locally:
```bash
curl -o openapi.json http://localhost:8000/openapi.json
```

## API Base Path

All API routes are under:
- `/api/v1`

See `README.md` for examples of common requests.
