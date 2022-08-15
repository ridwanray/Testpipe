# Pull official base image 
FROM python:3.9-slim

LABEL maintainer="danielale9291@gmail.com"
# Set working directory
WORKDIR /app

# Set env variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update \ 
    && apt-get install -y gcc python3-dev musl-dev libmagic1 libffi-dev \
    && pip install Pillow

COPY ./app/requirements ./requirements

# Install dependencies
COPY ./app/requirements ./requirements
RUN pip install --upgrade pip
RUN pip install -r ./requirements/prod.txt --use-deprecated=legacy-resolver

# Copy entrypoint.sh
COPY ./docker/prod/entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

COPY ./app /app

ENTRYPOINT [ "/entrypoint.sh" ]

