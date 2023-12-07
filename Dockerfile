FROM python:3.11
WORKDIR /usr/src/app
COPY . /usr/src/app
RUN mkdir -p /var/log
RUN pip install --no-cache-dir -r requirements.txt
CMD ["sh", "-c", "while true; do python pomodoro.py ; sleep 1; done"]
