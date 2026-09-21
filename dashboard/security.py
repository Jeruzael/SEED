"""Loopback is necessary, not sufficient: reject browser-origin and DNS-rebinding requests."""
import secrets
from starlette.responses import JSONResponse

CSP = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"


class SecurityMiddleware:
    def __init__(self, app, port, token, operator):
        self.app, self.token, self.operator = app, token, operator
        self.authority = f'127.0.0.1:{port}'
        self.origin = 'http://' + self.authority

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        pairs = scope.get('headers', [])
        headers = {k.lower(): v.decode('latin-1') for k, v in pairs}
        async def secured_send(message):
            if message['type'] == 'http.response.start':
                message.setdefault('headers', []).extend([
                    (b'content-security-policy', CSP.encode()), (b'x-content-type-options', b'nosniff'),
                    (b'referrer-policy', b'no-referrer'), (b'cache-control', b'no-store')])
            await send(message)
        async def reject(code, message, status):
            await JSONResponse({'error': {'code':code, 'message':message}}, status_code=status)(scope, receive, secured_send)
        if sum(k.lower() == b'host' for k, _ in pairs) != 1 or headers.get(b'host') != self.authority:
            return await reject('forbidden_host', 'Use the local 127.0.0.1 dashboard address.', 403)
        if headers.get(b'origin') not in (None, self.origin):
            return await reject('forbidden_origin', 'Cross-origin requests are not allowed.', 403)
        mutating = scope['method'] not in ('GET', 'HEAD', 'OPTIONS')
        if mutating:
            if headers.get(b'origin') != self.origin or not secrets.compare_digest(headers.get(b'x-seed-csrf', ''), self.token):
                return await reject('csrf_rejected', 'Refresh the dashboard before making changes.', 403)
            if headers.get(b'content-type', '').split(';')[0].strip().lower() != 'application/json':
                return await reject('json_required', 'JSON requests are required.', 415)
            try:
                if int(headers.get(b'content-length', '0')) > 16384:
                    return await reject('body_too_large', 'Request exceeds 16 KiB.', 413)
            except ValueError:
                return await reject('invalid_length', 'Invalid body length.', 400)
            body = bytearray()
            while True:
                message = await receive()
                if message['type'] == 'http.disconnect':
                    return
                body.extend(message.get('body', b''))
                if len(body) > 16384:
                    return await reject('body_too_large', 'Request exceeds 16 KiB.', 413)
                if not message.get('more_body', False):
                    break
            if not self.operator:
                return await reject('observer_only', 'Restart with --operator to enable owner changes.', 403)
            async def replay():
                return {'type':'http.request', 'body':bytes(body), 'more_body':False}
            return await self.app(scope, replay, secured_send)
        await self.app(scope, receive, secured_send)
