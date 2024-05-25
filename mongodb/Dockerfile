FROM python:3.9
ADD mongo_client.py .
ADD requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "-u", "mongo_client.py"]