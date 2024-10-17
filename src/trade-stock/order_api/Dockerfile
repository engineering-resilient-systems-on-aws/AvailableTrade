#FROM public.ecr.aws/docker/library/python:slim
FROM --platform=linux/amd64 public.ecr.aws/docker/library/python:3.9-slim as build

WORKDIR /usr/app
COPY requirements.txt .
RUN pip install -r requirements.txt # --no-cache-dir

COPY . .
CMD [ "gunicorn", "--bind", "0.0.0.0:80", "--log-config", "gunicorn_logging.conf", "--timeout", "2", "order_api:app" ]

#, "--workers", "3"