# Dockerfile

# 1. Choose a small Python base image
FROM python:3.12.9-slim

# 2. Prevent Python from writing .pyc files to disk and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Install system dependencies needed for psycopg2
RUN apt-get update && \
    apt-get install -y libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# 4. Create and set the working directory inside the container
WORKDIR /app

# 5. Copy your requirements and install them
COPY requirements.txt /app/

# 6. Install dependencies
RUN python -m venv /app/.venv && \
    . /app/.venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# 7. Copy the rest of your Django project code into the container
COPY . /app/

# 8. Expose the default Django port (change if needed)
EXPOSE 8000

# 9. Set the default command to run the Django development server or gunicorn
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
