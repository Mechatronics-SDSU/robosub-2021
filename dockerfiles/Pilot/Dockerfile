FROM ubuntu:latest

RUN apt-get -y update
RUN apt-get install python3 -y
ENV PYTHONPATH="${PYTHONPATH}:/"

RUN apt-get install python3-pip -y

ADD ./ ./
WORKDIR .

RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python3", "-u", "/src/Control/pilot_server.py" ]