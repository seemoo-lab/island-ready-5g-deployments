FROM python:3.10

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

COPY pobtog /app/pobtog

RUN pip install --upgrade pip && pip install -e pobtog

RUN pip install seaborn contextily

COPY plotting/plot_figures.py /app/plot_figures.py

ENTRYPOINT ["python", "/app/plot_figures.py"]

CMD []
