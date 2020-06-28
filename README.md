locald
======

`locald` is a library that helps run microservices (or even regular services)
in local development. It allows you to define service dependencies, restart
behavior, etc.

Configuration
=============

locald has a configuration file, locald.ini, which is a standard .ini file. In
it, you define any locald settings and any services locald should be managing.

A basic configuration that manages two services might look like:
```!ini
[locald]
pid_path=/tmp/myproject.pid

[cart_api]
service_path=cart.myproject.com/backend/myproject_cart_api/locald.service

[cart_www]
service_path=cart.myproject.com/frontend/locald.service
```

In this case, we define a `pid_path` for this specific instance of locald (as
you can run many, it is good to make them unique) and two services: a backend
API service (for example, flask application that you are running locally and a
frontend service, perhaps a react.js application.

Services can be defined either directly in the locald.ini file or using the
`service_path` directive, as shown here.

Configuration files for these services might look like:
```!ini
id=cart_api
description=Shopping Cart API
restart=always # or, never
restart_seconds=1 # if restarting, how many seconds to wait before doing so
command=/usr/bin/env python3 ../bin/serve.py
```

```!ini
id=cart_www
description=Shopping Cart Frontend
restart=always # or, never
restart_seconds=1 # if restarting, how many seconds to wait before doing so
command=yarn run start
requires=cart_api
```

In this example, `cart_www` indicates that it requires `cart_api`. locald will
determine that, if `locald start cart_www` is run, that `cart_api` must also be
running, and will start it if it is not.

Install
=======

`pip install locald`

Usage
=====

For full help, run `locald --help`.

`locald start <service>`: start the named service, and any dependencies.
`locald stop <service>`: stop the named service. only stops the named service, not any services it depends on.
`locald status`: show known services and their status.
