import os
import subprocess as sub

from werkzeug.urls import url_unquote
from werkzeug.utils import escape, redirect
from werkzeug.wrappers import Response

from auth import AuthManager, COOKIE_NAME
from bakery import render_path
from config import config
from tantilla import create_app, HTMLResponse, status


MOUNT_POINT = config["mount_point"]

auth_mgr = AuthManager(MOUNT_POINT)


def login(req):
    if req.method == 'POST':
        if "username" not in req.form or "password" not in req.form:
            return status(req, 400)
        username = req.form["username"]
        password = req.form["password"]

        auth_result = auth_mgr.try_log_in(username, password)
        if auth_result == AuthManager.USER_NOT_FOUND:
            return HTMLResponse(
                render_path("tmpl/login.htmo", {
                    "base": MOUNT_POINT,
                    "bad_username": True,
                    "bad_password": False,
                }),
                status=403,  # This one is iffy.
            )
        elif auth_result == AuthManager.PW_WRONG:
            return HTMLResponse(
                render_path("tmpl/login.htmo", {
                    "base": MOUNT_POINT,
                    "bad_username": False,
                    "bad_password": True,
                }),
                status=403,  # This one is iffy.
            )
        else:
            id_, expiration = auth_result
            from_ = url_unquote(req.args.get("from", ""))

            resp = redirect(MOUNT_POINT + from_, code=303)
            resp.set_cookie(COOKIE_NAME, id_, expires=expiration, secure=True)
            return resp

    if auth_mgr.cookie_to_username(req.cookies.get(COOKIE_NAME)):
        # Already logged in.
        return redirect(MOUNT_POINT, code=303)
    else:
        resp = HTMLResponse(
            render_path("tmpl/login.htmo", {
                "base": MOUNT_POINT,
                "bad_username": False,
                "bad_password": False,
            }),
        )
        resp.delete_cookie(COOKIE_NAME)
        return resp


@auth_mgr.require_auth
def home(req, username):
    if req.method == 'POST':
        if "url" not in req.form:
            return status(req, 400)

        p = sub.run(
            (
                "youtube-dl",
                "-x",
                "--audio-format", "mp3",
                "--get-filename",
                req.form["url"],
            ),
            universal_newlines=True,
            stdout=sub.PIPE,
            timeout=60,
        )
        if p.returncode != 0:
            return HTMLResponse(render_path("tmpl/error.htmo", {
                "base": MOUNT_POINT,
                "text": escape("Can't get video/audio name (don't know why)"),
            }))
        vid_name = p.stdout.strip()

        sub.run(("rm", "-rf", "dl/"))
        os.mkdir("dl")

        p = sub.run(
            (
                "youtube-dl",
                "-x",
                "--audio-format", "mp3",
                "-o", "dl/" + vid_name,
                req.form["url"],
            ),
            stdout=sub.DEVNULL,
            timeout=60,
        )
        if p.returncode != 0:
            return HTMLResponse(render_path("tmpl/error.htmo", {
                "base": MOUNT_POINT,
                "text": escape("Can't download (don't know why)"),
            }))

        mp3_name = vid_name[:vid_name.rfind('.')] + '.mp3'

        with open("dl/" + mp3_name, "rb") as f:
            return Response(
                f.read(),  # TODO
                headers=[(
                    'Content-Disposition',
                    'attachment; filename="{}"'.format(escape(mp3_name))
                )],
                content_type="audio/mpeg",
            )
    return HTMLResponse(
        render_path("tmpl/home.htmo", {
            "base": MOUNT_POINT,
            "title": "Audio downloader",
        })
    )


application = create_app(MOUNT_POINT, (
    ("", home),
    ("login", login),
))
