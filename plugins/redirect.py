from datasette import hookimpl


@hookimpl
def asgi_wrapper(datasette):
    def wrap_with_redirect(app):
        async def redirect_middleware(scope, receive, send):
            if scope["type"] == "http":
                headers = dict(scope.get("headers", []))
                host = headers.get(b"host", b"").decode()

                # Redirect apex domain to www
                if host == "followingthemoneyco.com":
                    path = scope.get("path", "/")
                    query_string = scope.get("query_string", b"")
                    location = "https://www.followingthemoneyco.com" + path
                    if query_string:
                        location += "?" + query_string.decode()
                    await send({
                        "type": "http.response.start",
                        "status": 301,
                        "headers": [
                            [b"location", location.encode()],
                        ],
                    })
                    await send({
                        "type": "http.response.body",
                        "body": b"",
                    })
                    return

            await app(scope, receive, send)

        return redirect_middleware

    return wrap_with_redirect