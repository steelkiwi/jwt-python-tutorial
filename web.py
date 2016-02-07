import json
from datetime import datetime, timedelta

from aiohttp import web
import jwt

from models import User

User.objects.create(email='user@email.com', password='password')

JWT_SECRET = 'secret'
JWT_ALGORITHM = 'HS256'
JWT_EXP_DELTA_SECONDS = 20


def json_response(body='', **kwargs):
    kwargs['body'] = json.dumps(body or kwargs['body']).encode('utf-8')
    kwargs['content_type'] = 'text/json'
    return web.Response(**kwargs)


async def login(request):
    post_data = await request.post()

    try:
        user = User.objects.get(email=post_data['email'])
        user.match_password(post_data['password'])
    except (User.DoesNotExist, User.PasswordDoesNotMatch):
        return json_response({'message': 'Wrong credentials'}, status=400)

    payload = {
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(seconds=JWT_EXP_DELTA_SECONDS)
    }
    jwt_token = jwt.encode(payload, JWT_SECRET, JWT_ALGORITHM)
    return json_response({'token': jwt_token.decode('utf-8')})

app = web.Application()
app.router.add_route('POST', '/login', login)
