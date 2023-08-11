FROM python:3.10

COPY requirements/ /requirements/
RUN pip install -r /requirements/docker.txt

COPY run.py /run.py
COPY tests/ /tests/
COPY app/ /app/
