FROM python:3.8.10

RUN apt-get update && apt-get install -y jq bash curl && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip3 install -r requirements.txt

WORKDIR /app

COPY . .

CMD ["kopf", "run", "main.py"]