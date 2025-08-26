FROM python:3.11

RUN mkdir -p /home/app

RUN addgroup app && adduser --system --no-create-home app --ingroup app

ENV HOME=/home/app

ENV APP_HOME=/home/app/

WORKDIR $APP_HOME

ENV PYTHONDONTWRITEBYTECODE=1

ENV PYTHONUNBUFFERED=1

RUN mkdir -p $APP_HOME/static
RUN pip install --upgrade pip

COPY ./requirements.txt $APP_HOME

RUN pip install -r requirements.txt
RUN apt-get update -y
COPY . $APP_HOME
RUN chown -R app:app $APP_HOME

USER app
