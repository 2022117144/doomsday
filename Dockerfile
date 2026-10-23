FROM python:3.11-alpine

WORKDIR /app

COPY integrations ./integrations
COPY data ./data
COPY glama.json ./glama.json
COPY README.md ./README.md

ENV PYTHONUNBUFFERED=1

CMD ["python3", "integrations/mcp/doomsday_mcp.py", "--mcp"]
