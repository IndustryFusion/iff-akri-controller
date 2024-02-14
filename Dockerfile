FROM python:3.8.10

COPY requirements.txt .

RUN pip3 install -r requirements.txt

COPY . .

WORKDIR /src
CMD ["kopf", "run", "main.py"]