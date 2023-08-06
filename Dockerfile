FROM python:3.9.17

COPY requirements/ /requirements/
RUN pip install -r /requirements/docker.txt

COPY run.py /run.py
COPY tests/ /tests/
COPY app/ /app/

WORKDIR /app
