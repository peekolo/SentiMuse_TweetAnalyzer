FROM python:3.7-slim-buster
WORKDIR /app
ADD requirements.txt /app
ADD SentiMuse-5e8cdc639edb.json /app
RUN pip3 install -r requirements.txt
EXPOSE 5000
ENV GOOGLE_APPLICATION_CREDENTIALS="/app/SentiMuse-5e8cdc639edb.json"
CMD python ./app.py