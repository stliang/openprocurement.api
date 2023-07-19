FROM python:3.8-alpine3.18

RUN apk --no-cache add gcc build-base git openssl-dev libffi-dev

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app
RUN pip install -e .

ENV TZ=Europe/Kiev
ENV LANG="en_US.UTF-8"
ENV LC_ALL="en_US.UTF-8"
ENV LC_LANG="en_US.UTF-8"
ENV PYTHONIOENCODING="UTF-8"
ENV PYTHONPATH "/app/src/:${PYTHONPATH}"

EXPOSE 80

CMD ["gunicorn", "--bind", "0.0.0.0:80", "-k", "gevent", "--paste", "/app/etc/service.ini", "--graceful-timeout=60", "--timeout=360"]
