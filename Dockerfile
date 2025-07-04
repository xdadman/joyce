FROM python:3.12.7
RUN groupadd -g 20 dialout || true
RUN useradd -u 1000 -G dialout -m pi
WORKDIR /usr/src/app
COPY requirements.txt /usr/src/app/
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py /usr/src/app/
COPY *.wav /usr/src/app/
CMD ["python", "-u", "./invertor_monitor_main.py"]

