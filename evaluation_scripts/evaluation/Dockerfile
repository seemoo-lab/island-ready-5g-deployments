FROM python:3.10

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

COPY evaluation/requirements.txt /app/requirements.txt

COPY pobtog /app/pobtog

RUN pip install --upgrade pip && pip install -e pobtog

COPY evaluation/evaluate-topology.py /app/evaluate-topology.py

ENTRYPOINT ["python", "/app/evaluate-topology.py"]

CMD []
