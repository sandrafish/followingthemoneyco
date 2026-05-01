from datasette.app import Datasette

@Datasette.hookimpl
def asgi_wrapper(datasette):
    async def redirect_middleware(scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            host = headers.get(b"host", b"").decode()
            
            # Redirect apex domain to www
            if host == "followingthemoneyco.com":
                await send({
                    "type": "http.response.start",
                    "status": 301,
                    "headers": [
                        [b"location", b"https://www.followingthemoneyco.com" + scope["path"].encode()],
                    ],
                })
                await send({
                    "type": "http.response.body",
                    "body": b"",
                })
                return
        
        await datasette.asgi(scope, receive, send)
    
    return redirect_middleware