import uvicorn

def main():
    import os
    env = os.getenv("ENV", "development")
    reload = env == "development"
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=reload)


if __name__ == "__main__":
    main()
