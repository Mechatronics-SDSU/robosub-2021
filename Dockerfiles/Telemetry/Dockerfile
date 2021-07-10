FROM ubuntu:latest

RUN apt-get -y update
RUN apt-get install python3 -y
ENV PYTHONPATH="${PYTHONPATH}:/"

RUN apt-get install python3-pip -y

ADD ./ ./
WORKDIR .

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python3", "/src/Control/telemetry_server.py" ]