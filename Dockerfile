# Dockerfile

# 1. Choose a small Python base image
FROM python:3.9-slim

# 2. Prevent Python from writing .pyc files to disk and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Create and set the working directory inside the container
WORKDIR /app

# 4. Copy your requirements and install them
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# 5. Copy the rest of your Django project code into the container
COPY . /app/

# 6. Expose the default Django port (change if needed)
EXPOSE 8000

# 7. Set the default command to run the Django development server or gunicorn
# Here we run the built-in dev server for simplicity.
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

