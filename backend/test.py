import uvicorn


def main():
    uvicorn.run("app.gateway.app:app", host="0.0.0.0", port=8001)


if __name__ == "__main__":
    main()
