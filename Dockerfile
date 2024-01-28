FROM python:3.10
WORKDIR /app
COPY . .
RUN curl -sSL https://sdk.cloud.google.com | bash
RUN pip install --upgrade pip && pip install mcrcon discord mcstatus google-cloud-compute
CMD ["python", "bot.py"]
