# **weather.metoffice** ![Codeship Status](https://codeship.com/projects/e7173200-c9e2-0133-bce4-0aabfff4550a/status?branch=krypton)

Weather plugin for Kodi. Fetches data from the UK Met Office.

## **Development and Testing**

Create a virtual env.

`python -m venv .venv`

Activate the virtual env.

`source .venv/bin/activate`

Install dependencies.

`pip install -r requirements.txt`

Run tests.

`python -m unittest discover`

## **Deployment**

Code is "deployed" by creating a PR against the repo-scripts repository.
