FROM ubuntu:latest

RUN apt-get -y update
RUN apt-get install -y libgl1-mesa-dev libglib2.0-0 libsm6 libxrender1 libxext6 
RUN apt-get install python3 -y
ENV PYTHONPATH="${PYTHONPATH}:/"

RUN apt-get install python3-pip -y

ADD ./ ./
WORKDIR .

RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python3", "/gui/video_server.py" ]
