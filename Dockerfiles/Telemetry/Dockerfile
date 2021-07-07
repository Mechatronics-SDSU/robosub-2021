FROM python:3

ENV PYTHONPATH="${PYTHONPATH}:/"
ADD ./ ./
WORKDIR .

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python", "/src/Control/telemetry_server.py" ]