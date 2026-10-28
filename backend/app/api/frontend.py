"""Optional same-origin SPA hosting for the Render deployment."""

from pathlib import Path

from fastapi import FastAPI
from starlette.exceptions import HTTPException
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles


class FrontendFiles(StaticFiles):
    async def get_response(self, path, scope):
        first = path.split("/", 1)[0]
        if first == "api":
            raise HTTPException(404)
        try:
            response = await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code != 404 or scope["method"] not in {"GET", "HEAD"}:
                raise
            if first == "assets" or Path(path).suffix:
                raise
            response = FileResponse(Path(self.directory) / "index.html")
        response.headers["Cache-Control"] = (
            "public, max-age=31536000, immutable" if first == "assets" else "no-store"
        )
        return response


def register_frontend(app: FastAPI, directory: str) -> None:
    if not (Path(directory) / "index.html").is_file():
        raise RuntimeError("FRONTEND_DIST_DIR must contain a built index.html")
    app.state.serves_frontend = True
    app.mount("/", FrontendFiles(directory=directory, html=True), name="frontend")
