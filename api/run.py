"""Script to run the FastAPI server."""
import uvicorn

def main():
    """Run the FastAPI server."""
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Enable auto-reload during development
    )

if __name__ == "__main__":
    main() 