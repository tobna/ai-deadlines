# Use an official Alpine-based Python image as your base
FROM python:3.9-alpine

# Set the working directory
WORKDIR /app

# Install git and other build dependencies (if your Python packages require compilation)
# It's good practice to install build dependencies and then remove them in the same RUN layer
# to keep the final image size down.
RUN apk add --no-cache git openssh-client # openssh-client if you need to clone private repos via SSH

# Install Python build dependencies (e.g., for packages with C extensions)
# Common ones include build-base, libffi-dev, openssl-dev.
# Add more as needed based on your requirements.txt.
RUN apk add --no-cache --virtual .build-deps \
    build-base \
    libffi-dev \
    openssl-dev \
    # Add any other -dev packages your Python libraries might need
    # e.g., if you have psycopg2, you'd need postgresql-dev
    # if you have Pillow, you might need zlib-dev, jpeg-dev, etc.
    && pip install --upgrade pip

# Install Python dependencies
RUN pip install --no-cache-dir requests bs4 pytz pyyaml dateparser loguru

# Remove build dependencies to keep the image small
RUN apk del .build-deps

