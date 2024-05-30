# Bidsificator

A PyQt application to manage those BIDS files using a GUI.

## Develop

Use `poetry` (installed via `pipx`) to setup the virtual env and run it nicely for you.

```console
# Pick a valid Python3 version, e.g. 3.10 or 3.11
$ poetry env use $(pyenv which python3.10)

$ poetry env use $(pyenv which python3.11)

$ poetry install
```

Running the UI.

```console
$ poetry run bidsificator
```

Running the web server (in debug mode), use `gunicorn` or else in production.

```console
$ poetry run bidsificator-api
```

### UI

Opening the Qt designer with the form.

```console
$ poetry run make design
```

And then rebuilding the Python file from it.

```console
$ poetry run make build-ui
```

## Package

To be continued...
