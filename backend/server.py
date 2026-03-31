from fastapi import FastAPI
from app.gateway.app import create_app

app = FastAPI(title="DeerFlow Report Service")
app.mount("/ReportService/rest", create_app())
