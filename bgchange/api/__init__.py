"""The optional web API: the same tool as the `bgchange` command, over HTTP.

The CLI is the main way to use the project; this API exists so a web page
(step 9) can use it. It calls the same change_background() as the CLI, so the
results are identical.

    GET  /api/health              is the server up, is the model loaded?
    POST /api/change-background   photo + colour (+ shadow options) -> PNG
    GET  /docs                    interactive documentation, made by FastAPI

One file per job (see docs/08b-api.md):

    settings.py   the options, read from environment variables (model, upload limit, ...)
    routes.py     the 2 routes
    app.py        create_app(): builds the app, loads the model once at start-up
    server.py     the `bgchange-api` command that starts the server

Start it:

    uv run bgchange-api                 # http://127.0.0.1:8000/docs
"""
