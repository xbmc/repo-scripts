# **weather.metoffice [deprecated]** ![Codeship Status](https://codeship.com/projects/e7173200-c9e2-0133-bce4-0aabfff4550a/status?branch=krypton)

Weather plugin for Kodi. Fetches data from the UK Met Office.

This addon is now deprecated.

## Getting Started

A map of weather stations for observation (ie current weather) can be found here:
https://www.metoffice.gov.uk/weather/guides/observations/uk-observations-network

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
