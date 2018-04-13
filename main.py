from bakery import render_path
from config import config
from tantilla import create_app, HTMLResponse, status


MOUNT_POINT = config["mount_point"]


def hello(req):
    if req.method == 'POST':
        return status(req, 400)
    return HTMLResponse(
        render_path("tmpl/hello.htmo", {
            "base": MOUNT_POINT,
            "title": "hey",
        })
    )


application = create_app(MOUNT_POINT, (
    ("hello", hello),
))
