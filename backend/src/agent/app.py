# mypy: disable - error - code = "no-untyped-def,misc"
import os
import pathlib
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
import fastapi.exceptions
from pydantic import BaseModel
from agents import Agent, Runner, function_tool
from agents.extensions.models.litellm_model import LitellmModel
from google.generativeai import Client

# Define the FastAPI app
app = FastAPI()


def create_frontend_router(build_dir="../frontend/dist"):
    """Creates a router to serve the React frontend.

    Args:
        build_dir: Path to the React build directory relative to this file.

    Returns:
        A Starlette application serving the frontend.
    """
    build_path = pathlib.Path(__file__).parent.parent.parent / build_dir
    static_files_path = build_path / "assets"  # Vite uses 'assets' subdir

    if not build_path.is_dir() or not (build_path / "index.html").is_file():
        print(
            f"WARN: Frontend build directory not found or incomplete at {build_path}. Serving frontend will likely fail."
        )
        # Return a dummy router if build isn't ready
        from starlette.routing import Route

        async def dummy_frontend(request):
            return Response(
                "Frontend not built. Run 'npm run build' in the frontend directory.",
                media_type="text/plain",
                status_code=503,
            )

        return Route("/{path:path}", endpoint=dummy_frontend)

    build_dir = pathlib.Path(build_dir)

    react = FastAPI(openapi_url="")
    react.mount(
        "/assets", StaticFiles(directory=static_files_path), name="static_assets"
    )

    @react.get("/{path:path}")
    async def handle_catch_all(request: Request, path: str):
        fp = build_path / path
        if not fp.exists() or not fp.is_file():
            fp = build_path / "index.html"
        return fastapi.responses.FileResponse(fp)

    return react


# Mount the frontend under /app to not conflict with the LangGraph API routes
app.mount(
    "/app",
    create_frontend_router(),
    name="frontend",
)


genai_client = Client(api_key=os.getenv("GEMINI_API_KEY"))


@function_tool
def google_search(query: str) -> str:
    """Run a Google search using the Gemini API."""
    response = genai_client.models.generate_content(
        model="gemini-2.0-flash",
        contents=query,
        config={"tools": [{"google_search": {}}], "temperature": 0},
    )
    return response.text


DEFAULT_MODEL = os.getenv("AGENT_MODEL", "gemini/gemini-2.5-flash-preview-04-17")

base_agent = Agent(
    name="Gemini Research Agent",
    instructions="Use the google_search tool to gather information and answer the user question with citations.",
    model=LitellmModel(model=DEFAULT_MODEL, api_key=os.getenv("GEMINI_API_KEY")),
    tools=[google_search],
)


class ChatRequest(BaseModel):
    question: str
    model: str | None = None


@app.post("/api/chat")
async def chat(req: ChatRequest):
    agent = base_agent if not req.model else base_agent.clone(
        model=LitellmModel(model=req.model, api_key=os.getenv("GEMINI_API_KEY"))
    )
    result = await Runner.run(agent, req.question)
    return {"answer": result.final_output}

