FROM python:3.8-slim-buster
WORKDIR /opt/cyst
COPY . /opt/cyst
RUN pip3 install -r requirements.txt
RUN chmod +x tools/runner/runner.py
ENV PYTHONPATH=/opt/cyst
CMD ["python", "/opt/cyst/tools/runner/runner.py"]