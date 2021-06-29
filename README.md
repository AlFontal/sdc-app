# SDCpy app

<img src="https://raw.githubusercontent.com/AlFontal/sdcpy-app/master/static/sdcpy_logo_black.png" width="200" height="250" />

Simple web app built with [Dash](https://dash.plotly.com/) and hosted in Heroku to enable a web-based 
GUI for Scale Dependent Correlation analysis.

Current deployment of the app (still in the very *alpha* phase) can be accessed in https://sdcpy-app.herokuapp.com/.

### Current Limitations

One of the main constraints of the deployed app is Heroku's 30 second timeout for requests.
If a request to Heroku's dyno takes longer than 30 second to get back to the router it will be 
terminated, and the app will stay awaiting for a response completely unaware of the fact that
its requests has been terminated. This is specially annoying considering that computation of SDC
can easily get over 30 secs if the time series is long enough (specially when using Spearman instead
of Pearson as the correlation metric). 

A proper way of handling this would  involve using asynchronous tasks handlers, which would possibly
work using a combination of Redis and Celery, and I will try to do so if I find the time as this
seems to be the solution with best practices. 
Another (hacky) alternative would be to modify `sdcpy`'s code to periodically pipe some output (such
as tqdm's progress bar) which could be fetched by the app and use to inform a dash progress bar which
would effectively keep the service awake. Migrating to another service such as AWS Elastic Beanstalk
might help, but it still appears to have a hard cap of 60 sec timeout and loses the *forever free* appeal
of Heroku (and domain names are paid).

So far, the best way to use the app if you intend to run long computations is to run it locally, so:

### Running Locally

In order to run the app locally, you will need to have Python >= 3.8 installed on your system and to
include the project dependencies. The project is set up to use `poetry` to handle dependencies, so
just run:
```
poetry install
```
And it should set up a virtual environment and install the dependencies defined in `pyproject.toml`.
To run the app just use:
```
poetry run python app.py
```
And a running version of the app should be accessible in your machine's `8050` port: http://localhost:8050

If you can't/don't want to use `poetry`, there is a `requirements.txt` file because Heroku requires it,
so a regular virtualenv installation using `venv` and `pip` should suffice.


