FROM --platform=linux/amd64 public.ecr.aws/docker/library/python:3-slim as build
# for local only, if using mac M1
#FROM  public.ecr.aws/docker/library/python:slim as build

WORKDIR /usr/app
COPY requirements.txt .
RUN pip install -r requirements.txt # --no-cache-dir

COPY . .

# curl "$ECS_CONTAINER_METADATA_URI/task" -o "$HOME/results.json"
  #cat "$HOME/results.json"

CMD [ "gunicorn", "--bind", "0.0.0.0:80", "--log-config", "gunicorn_logging.conf", "--timeout", "1", "confirms_api:app" ]


# local testing
# docker image build -t confirms .
# docker run -p 80:80 -d confirms