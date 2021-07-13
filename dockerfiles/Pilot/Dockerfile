FROM ubuntu:latest

RUN apt-get -y update
RUN apt-get install python3 -y
ENV PYTHONPATH="${PYTHONPATH}:/"

RUN apt-get install python3-pip -y

ADD ./ ./
WORKDIR .
EXPOSE 50004

RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python3", "/src/Control/pilot_client.py" ]