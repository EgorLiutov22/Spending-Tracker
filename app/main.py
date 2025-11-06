from fastapi import FastAPI


app = FastAPI(title="Spending Tracker API")

@app.get("/")
def root():
    return {"message": "Hello"}