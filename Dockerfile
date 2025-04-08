FROM python:3.9-slim
# Install Chrome dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    default-jdk \
    curl \
    apt-utils
# Install Chrome with updated key handling
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor > /usr/share/keyrings/google-chrome.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable
# Set up working directory
WORKDIR /app
# Force specific NumPy version
RUN pip install --no-cache-dir numpy==1.24.3
# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Force NumPy version again
RUN pip install --no-cache-dir numpy==1.24.3 --force-reinstall

# Create the keys directory
RUN mkdir -p /app/keys

# Copy application code
COPY . .

# Make sure the credentials file exists in the container
# Either uncomment this line if the key is in your local directory:
# COPY keys/fast-tensor-455801-h0-7c50fd901145.json /app/keys/
# Or create an empty placeholder file (not recommended for production)
RUN touch /app/keys/fast-tensor-455801-h0-7c50fd901145.json

# Run the ChromeDriver installer script
RUN pip install requests && python install_chromedriver.py
# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99
# Run the app with increased timeout
CMD exec gunicorn --bind :$PORT --timeout 900 --workers 1 --threads 4 app:app