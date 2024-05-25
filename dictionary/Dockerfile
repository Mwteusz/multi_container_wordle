FROM python:3.9
ADD dictionary.py .
ADD requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "-u", "dictionary.py"]