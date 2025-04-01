FROM python:3.12.5-slim

ENV PYTHONBUFFERED=1
# Set the working directory inside the container
WORKDIR /MAT

# Upgrade pip
RUN pip install --upgrade pip

# Copy the Django project  and install dependencies
COPY requirements.txt  /MAT/

# Upgrade pip
RUN pip install --upgrade pip

RUN pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

