import io
import base64
import dash

import pandas as pd
import matplotlib.pyplot as plt
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import sdcpy.scale_dependent_correlation as sdc

from whitenoise import WhiteNoise
from dash.exceptions import PreventUpdate
from dash.dependencies import Output, Input, State

app = dash.Dash(
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)

app.title = 'SDCpy app'
server = app.server
server.wsgi_app = WhiteNoise(server.wsgi_app, root='static/')

GITHUB_LOGO = 'github_logo_white.png'
SDCPY_LOGO = 'sdcpy_logo_white.png'
SIDEBAR_STYLE = {
    'position': 'fixed',
    'top': 0,
    'left': 0,
    'bottom': 0,
    'width': '10rem',
    'padding': '2rem 1rem',
    'background-color': '#343A40',
}

sidebar = html.Div(
    [
        html.A(
            dbc.Row(
                [html.Img(src=SDCPY_LOGO, height='140px',
                          style={'margin-left': '15px'})],
                align='center',
                no_gutters=False,
            ),
            href='https://github.com/AlFontal/sdcpy',
        ),
        html.Hr(),
        dcc.Markdown('**Source Code**', style={'color': 'white', 'margin-left': '20px'}),
        html.A(
            dbc.Row(
                [html.Img(src=GITHUB_LOGO, height='60px',
                          style={'margin-left': '50px'})],
                align='center',
                no_gutters=False,
            ),
            href='https://github.com/AlFontal/sdcpy-app',
        ),
    ], style=SIDEBAR_STYLE,
)

data_memory_store = dcc.Store(id='data-memory-store')
clicks_store = dcc.Store(id='clicks-store', data=0)
results_store = dcc.Store(id='results-store', data=None)

# To make sure our site does not reach Heroku's 30s time-out, update hidden div every 15s
interval = dcc.Interval(id='interval', interval=15 * 1000)
hidden_div = html.Div(id='hidden-div')


@app.callback(Output('hidden-div', 'children'),
              Input('interval', 'n_intervals'))
def interval_update(n):
    return(html.P(str(n)))


title_row = dcc.Markdown('## Scale dependent correlation Analysis WebApp')

instructions_row = dcc.Markdown('Start by uploading a `.csv` file containing at the very least a'
                                ' single column with a column header and numerical values.',
                                style={'width': '800 px'})

ts1_dropdown = dcc.Dropdown(options=[{'label': 'Add dataset to select', 'value': 'Empty'}],
                            placeholder='Select time series 1', id='ts1-dropdown')
ts2_dropdown = dcc.Dropdown(options=[{'label': 'Add dataset to select', 'value': 'Empty'}],
                            placeholder='Select time series 2', id='ts2-dropdown')
date_dropdown = dcc.Dropdown(options=[{'label': 'Add dataset to select', 'value': 'Empty'}],
                             placeholder='Select date column', id='date-dropdown')
method_dropdown = dcc.Dropdown(options=[{'label': 'Spearman', 'value': 'spearman'},
                                        {'label': 'Pearson', 'value': 'pearson'}],
                               placeholder='Select correlation method', id='method-dropdown')

parameter_rows = html.Div(
    [dcc.Markdown('Now select the parameters to run the SDC Analysis:'),
     dbc.Row([
         dbc.Col([html.B('Time Series 1'), ts1_dropdown], align='center'),
         dbc.Col([html.B('Time Series 2'), ts2_dropdown], align='center'),
         dbc.Col([html.B('Date Column'), date_dropdown], align='center'),
     ], style={'width': '700px'}),
     html.Br(),
     dbc.Row([
         dbc.Col([html.B('Corr. Method'), method_dropdown], align='center'),
         dbc.Col([html.B('Min Lag'),
                  dbc.Input(id='min-lag', placeholder='Select min lag', type='number')]),
         dbc.Col([html.B('Max Lag'),
                  dbc.Input(id='max-lag', placeholder='Select max lag', type='number')]),
         dbc.Col([html.B('Window Size (s)'),
                  dbc.Input(id='window', placeholder='Select window size', type='number', min=0)])
     ], style={'width': '700px'})
     ], hidden=True, id='parameters-div')

file_upload = html.Div([
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            'Upload dataset (.csv)',
            html.A('')
        ]),
        style={
            'width': '500px',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px',
            'margin-left': '2 rem'
        }
    ),
    html.Div(id='output-data-upload'),
])
progress_div = html.Div(id='progress-div')
results_div = html.Div(id='results-div')

run_button = html.Div(dbc.Button('Run SDC Analysis',
                                 disabled=False,
                                 style={'margin': '10px'},
                                 id='run-button'),
                      id='run-button-div',
                      hidden=True)


def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))

    except Exception as e:
        print(e)
        return dbc.Alert('There was an error processing this file. Please upload a valid .csv file')

    return df.to_dict()


@app.callback([Output('data-memory-store', 'data'),
               Output('upload-data', 'children'),
               Output('parameters-div', 'hidden'),
               Output('run-button-div', 'hidden')],
              Input('upload-data', 'contents'),
              State('upload-data', 'filename'))
def update_output(content, filename):
    if content is not None:
        children = parse_contents(content, filename)
        return children, html.P(filename), False, False
    else:
        raise PreventUpdate


@app.callback([Output('ts1-dropdown', 'options'),
               Output('ts2-dropdown', 'options'),
               Output('date-dropdown', 'options')],
              Input('data-memory-store', 'data'))
def update_series(data):
    if data is not None:
        df = pd.DataFrame(data)
        options = [{'value': col, 'label': col} for col in df.columns]
        return options, options, options
    else:
        raise PreventUpdate


@app.callback([Output('progress-div', 'children'),
               Output('clicks-store', 'data')],
               Input('run-button', 'n_clicks'),
               Input('clicks-store', 'data'),
               )
def on_run_sdc_click_progress(n_clicks, current_clicks):
    if n_clicks is not None and n_clicks > current_clicks:
        return [dcc.Markdown('Computing SDC'), dbc.Spinner()], n_clicks

    else:
        raise PreventUpdate


@app.callback([Output('results-div', 'children'),
               Output('progress-div', 'hidden')],
              Input('progress-div', 'children'),
              State('ts1-dropdown', 'value'),
              State('ts2-dropdown', 'value'),
              State('date-dropdown', 'value'),
              State('method-dropdown', 'value'),
              State('min-lag', 'value'),
              State('max-lag', 'value'),
              State('window', 'value'),
              State('data-memory-store', 'data')
              )
def on_run_sdc_click(trigger, ts1, ts2, date, method, min_lag, max_lag, w, data):
    if trigger is not None:
        df = pd.DataFrame(data).assign(date=lambda dd: pd.to_datetime(dd[date])).set_index('date')
        computed_sdc = sdc.SDCAnalysis(ts1=df[ts1], ts2=df[ts2], method=method,
                                       min_lag=min_lag, max_lag=max_lag, fragment_size=w)
        buffer = io.BytesIO()
        computed_sdc.combi_plot(xlabel=ts1, ylabel=ts2, wspace=.3, hspace=.3, max_lag=max_lag,
                                min_lag=min_lag, figsize=(6, 6), title='')
        plt.savefig(buffer, format='png', dpi=150)
        plt.close()
        data = base64.b64encode(buffer.getbuffer()).decode("utf8")
        image_div = html.Img(src=f'data:image/png;base64,{data}', id='sdc-results-img')
        download_button = html.Div([
        dbc.Button("Download Results Table", id="download-button"),
        dcc.Download(id="download-results-xlsx")
                ])
        return [dcc.Markdown('### SDC Analysis Results'), download_button, image_div], True

    else:
        raise PreventUpdate


@app.callback(
    Output("download-results-xlsx", "data"),
    Input("download-button", "n_clicks"),
    Input("results-store", "data"),
    prevent_initial_call=True,
)
def on_download_click(n_clicks, data):
    if n_clicks is not None and n_clicks > 0:
        return dict(content=data, filename='test.xslx')


content_div = html.Div([title_row,
                        html.Hr(),
                        instructions_row,
                        file_upload,
                        parameter_rows,
                        html.Br(),
                        run_button,
                        html.Hr(),
                        progress_div,
                        results_div],
                       style={'margin-left': '10rem', 'margin-right': '2rem',
                              'padding': '2rem 1rem'})

app.layout = html.Div(children=[sidebar,
                                content_div,
                                data_memory_store,
                                clicks_store,
                                results_store,
                                interval,
                                hidden_div])


if __name__ == '__main__':
    app.run_server()
