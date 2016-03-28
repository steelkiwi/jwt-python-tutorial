This repo contains examples from [article in our blog](http://steelkiwi.com/blog/jwt-authorization-python-part-1-practice/).

From Introduction to JSON Web Tokens: JSON Web Token (JWT) is an open standard (RFC 7519) that defines a compact and self-contained way for securely transmitting information between parties as a JSON object. This information can be verified and trusted because it is digitally signed. JWTs can be signed using a secret (with HMAC algorithm) or a public/private key pair using RSA.
Introduction to JSON Web Tokens is great by itself, so here I'll show how to implement trivial JWT authentication in Python.

This article assumes Python 3.5 to use nice asyncio coroutine syntax.

We will use aiohttp as http library, gunicorn as development server with --reload. pyjwt is python implementation of JWT standard. Requirements for the tutorial are listed at requirements.txt on github page. Install it in virtualenv with:

```
pip install -r requirements.txt
```

As it is a demo application, there is not much error handling, but only essential code to show how to use JWT.
