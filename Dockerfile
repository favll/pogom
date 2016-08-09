#Docker image for pogom

FROM python:2.7-alpine

# Default port the webserver runs on
EXPOSE 5000

# Working directory for the application
WORKDIR /usr/src/app

# Set Entrypoint
ENTRYPOINT ["python", "./runserver.py", "-H", "0.0.0.0", "-P", "5000"]

# Install required system packages
RUN apk add --no-cache ca-certificates
RUN apk add --no-cache bash git openssh

COPY requirements.txt /usr/src/app/

RUN apk add --no-cache build-base \
 && pip install --no-cache-dir -r requirements.txt \
 && apk del build-base

COPY static /usr/src/app/static

COPY . /usr/src/app/
