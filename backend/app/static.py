"""Serve the packaged SPA on the same origin as the API on a free web service."""

from pathlib import Path

from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles

CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' https: http: data:; font-src 'self'; connect-src 'self'; "
    "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
)


class SPAFiles(StaticFiles):
    def __init__(self, directory: Path):
        super().__init__(directory=directory, html=True)
        if not (directory / "index.html").is_file():
            raise RuntimeError("The packaged frontend index.html is missing")

    async def get_response(self, path, scope):
        # Starlette использует разделитель ОС; защита API должна работать и на Windows.
        normalized = path.replace("\\", "/").lstrip("/")
        api = normalized == "api" or normalized.startswith("api/")
        if api:
            raise HTTPException(404)
        try:
            response = await super().get_response(path, scope)
        except HTTPException as error:
            if (
                error.status_code != 404
                or normalized.startswith(("assets/", "images/", "brand/"))
                or Path(path).suffix
            ):
                raise
            response = await super().get_response("index.html", scope)
        response.headers["Cache-Control"] = (
            "public, max-age=31536000, immutable"
            if normalized.startswith("assets/")
            else "no-cache"
        )
        return response
