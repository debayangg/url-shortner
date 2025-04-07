from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import asyncio

from database import init_pool, insert_url, get_link, full_sync, background_tasks
from codeGenerator import get_code_for_new_url, generate_codes_if_needed

load_dotenv()
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

app = FastAPI()

class URLRequest(BaseModel):
    url: str

@app.on_event("startup")
async def startup_event():
    await init_pool()  # Initialize the asyncpg pool
    await full_sync() # Sync the local SQLite db with PostgreSQL
    print("Database initialized at startup.")
    # Generate codes if needed during startup:
    await generate_codes_if_needed()

@app.post("/shorten")
async def shorten_url(req: URLRequest):
    code = await get_code_for_new_url()  # Await the async code generator
    if not code:
        raise HTTPException(status_code=500, detail="No available codes")
    await insert_url(code, req.url)
    return {"short_url": f"http://localhost:8000/{code}"}

@app.get("/{code}")
async def redirect_to_url(code: str):
    link = get_link(code)
    if not link:
        raise HTTPException(status_code=404, detail="URL not found")
    return RedirectResponse(link)

@app.on_event("shutdown")
async def shutdown_event():
    if background_tasks:
        print(f"Waiting for {len(background_tasks)} background tasks to finish...")
        await asyncio.gather(*background_tasks)
