FROM python:3.10

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

COPY pobtog /app

RUN pip install --upgrade pip && pip install -e .

COPY generation/generate-topology.py /app/generate-topology.py

ENTRYPOINT ["python", "/app/generate-topology.py"]

CMD []
