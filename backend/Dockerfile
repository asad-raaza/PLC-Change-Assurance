FROM python:3.11-slim
WORKDIR /opt/pcaf
COPY requirements.txt /opt/pcaf/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend /opt/pcaf/backend
COPY simulator /opt/pcaf/simulator
COPY experiments /opt/pcaf/experiments
COPY policies /opt/pcaf/policies
ENV PYTHONPATH=/opt/pcaf/backend:/opt/pcaf
WORKDIR /opt/pcaf/backend
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
