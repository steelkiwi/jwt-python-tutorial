> **From [Introduction to JSON Web Tokens](https://jwt.io/introduction/):**
> JSON Web Token (JWT) is an open standard (RFC 7519) that defines a compact and self-contained way for securely transmitting information between parties as a JSON object. This information can be verified and trusted because it is digitally signed. JWTs can be signed using a secret (with HMAC algorithm) or a public/private key pair using RSA.


**Introduction to JSON Web Tokens** is great by itself, so here I'll show how to implement trivial JWT authentication in Python.

This article assumes Python 3.5 to use nice asyncio coroutine syntax.

We will use `aiohttp` as http library, `gunicorn` as development server with `--reload`. `pyjwt` is python implementation of JWT standard. Requirements for the tutorial are listed at [requirements.txt](https://github.com/steelkiwi/jwt-python-tutorial/blob/master/requirements.txt) on [github page](https://github.com/steelkiwi/jwt-python-tutorial). Install it in virtualenv with:

    :::sh
    pip install -r requirements.txt

As it is a demo application, there is not much error handling, but only essential code to show how to use JWT.

### Initial setup

At first, lets create a wrapper for `aiohttp.web.Response` where we `dumps` body to json and assign the suitable content type:

    :::python
    import json
    from aiohttp import web

    def json_response(body='', **kwargs):
        kwargs['body'] = json.dumps(body or kwargs['body']).encode('utf-8')
        kwargs['content_type'] = 'text/json'
        return web.Response(**kwargs)
There is a `User` model in the helper module `models`. It makes it possible to get and create users in the memory to meet our need for a simple storage mechanism. We will need to import it and create the user to work with it further:

    :::python
    from models import User
    User.objects.create(email='user@email.com', password='password')

### Login
Next, create a handler to allow the client to login, i.e. acquire authentication token.

    :::python
    from datetime import datetime, timedelta
    import jwt

    JWT_SECRET = 'secret'
    JWT_ALGORITHM = 'HS256'
    JWT_EXP_DELTA_SECONDS = 20

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

Here is a step-by-step breakdown of the process:

1. Get data from post query.
2. Fetch user by email from storage.
3. Check if passwords match.
4. If the user with the email does not exist or the password doesn't match, return response with error message.
5. Next, create *token payload*, where we store data we'd like to have when authorized clients perform certain actions. There are *reserved keys*, like `exp`, which JWT standard defines and its implementations use internally to provide additional features. In our case, we store the user ID to identify user and expiration date, after which the token becomes invalid. Description of `exp` and other reserved keys provided in corresponding [RFC section](https://tools.ietf.org/html/rfc7519#section-4.1)
6. Finally, we encode our payload with a secret string and specified algorithm and the return response with a token in the JSON body.

In order to ask `aiohttp` to use this handler, we should create `Application` and `add_route` with `login` handler.

The code at this point is available [here](https://github.com/steelkiwi/jwt-python-tutorial/tree/9527a2f2fd27c70e4cfaacd0605ed40a6b54a5c2). If you follow along, clone the repo, and run`git checkout login-url`

Now, to check if everything OK, run `gunicorn`:

    :::sh
    gunicorn web:app --bind localhost:8080 --worker-class aiohttp.worker.GunicornWebWorker --reload

And issue request to `/login` url:

    :::sh
    http -f post localhost:8080/login email=user@email.com password=password

You should see something like this:

    :::httpie
    HTTP/1.1 200 OK
    CONNECTION: keep-alive
    CONTENT-LENGTH: 134
    CONTENT-TYPE: text/json
    SERVER: Python/3.5 aiohttp/0.18.4

    {
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE0NTQ4ODEwOTh9.POQjZyC6OtqlFjmzh5S8jKkxdM90PAvI4GHzTpKwIF4"
    }

### Auth middleware 

Now we can acquire the token. We can store it in client and use it to get access to the user's resources. Next we create middleware that will fetch a user and add it to the response object.

Here is the code (add it to `web.py`):

    :::python
    async def get_user(request):
        return json_response({'user': str(request.user)})

    async def auth_middleware(app, handler):
        async def middleware(request):
            request.user = None
            jwt_token = request.headers.get('authorization', None)
            if jwt_token:
                try:
                    payload = jwt.decode(jwt_token, JWT_SECRET,
                                         algorithms=[JWT_ALGORITHM])
                except (jwt.DecodeError, jwt.ExpiredSignatureError):
                    return json_response({'message': 'Token is invalid'}, status=400)

                request.user = User.objects.get(id=payload['user_id'])
            return await handler(request)
        return middleware

    app = web.Application(middlewares=[auth_middleware])
    app.router.add_route('GET', '/get-user', get_user)

Let’s go through it step-by-step:

1. Define the aiohttp middleware.
2. Get token from `AUTHORIZATION` header, if there is one.
3. Try to decode it with the same secret and encoding algorithm as it was created.
4. If token expired or decoding error occurs, return response with error message.
5. If everything OK, fetch user by with `user_id` in `payload` and assign it to `request.user`.
6. Note that `middlewares=[auth_middleware]` added to `Application` instance creation.
7. Also, url handler to check `request.user`.

Code is in [the commit](https://github.com/steelkiwi/jwt-python-tutorial/tree/09ffd2f6477ba6008bc726048f70e61311dc7600). Or `git checkout auth-middleware` if have cloned repo.

Ensure, that gunicorn is running, get token from `/login` url, and use it in `/get-user` url:

    :::sh
    http -f post localhost:8080/login email=user@email.com password=password
    http localhost:8080/get-user authorization:<token>

If token is invalid or expired, you'll get an error message.
If successful, you'll see user info printed in the console:

    :::httpie
    HTTP/1.1 200 OK
    CONNECTION: keep-alive
    CONTENT-LENGTH: 55
    CONTENT-TYPE: text/json
    SERVER: Python/3.5 aiohttp/0.18.4

    {
        "user": "User id=1: <user@email.com, is_admin=False>"
    }

OK, that’s great! Now we can use the user in our views. 

In essence, all further actions are not related to the authentication mechanism. For example, it is common to have something to ensure, that only logged in users have access to specific handlers. Let’s write a simple decorator to accomplish this task:

    :::python
    def login_required(func):
        def wrapper(request):
            if not request.user:
                return json_response({'message': 'Auth required'}, status=401)
            return func(request)
        return wrapper

Here, we just check if `request.user` is a truthy value. If it is not, it should return a response with an error message.
