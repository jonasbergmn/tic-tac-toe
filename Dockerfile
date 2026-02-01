# ---- Builder stage ----
FROM python:3.13-slim AS builder

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Create venv and install dependencies
RUN uv venv && uv sync

# ---- Final stage ----
FROM python:3.13-slim AS final

# Create a non-root user and switch to it
RUN useradd --create-home appuser
USER appuser

WORKDIR /app

# Copy venv from builder
COPY --from=builder --chown=appuser:appuser /app/.venv ./.venv

# Copy application code
COPY --chown=appuser:appuser ./app ./app

# Use venv
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
