@echo off
pip install -r requirements.txt
if not exist cert.pem (
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout key.pem -out cert.pem -subj "/C=US/ST=State/L=City/O=Org/OU=Dev/CN=localhost"
)
python app.py
pause
