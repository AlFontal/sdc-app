import dash
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import pandas as pd
from dash.dependencies import Output, Input, State
from dash.exceptions import PreventUpdate
import sdcpy.scale_dependent_correlation as sdc
import base64
import io
import matplotlib.pyplot as plt

app = dash.Dash(
    external_stylesheets=[dbc.themes.BOOTSTRAP]
)
GITHUB_LOGO = 'assets/github_logo_white.png'
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
                [html.Img(src='assets/sdcpy_logo_white.png', height='140px',
                         style={'margin-left': '15px'})],
                align='center',
                no_gutters=False,
            ),
            href='https://github.com/AlFontal/sdcpy',
        ),
        html.Hr()], style=SIDEBAR_STYLE,
)


data_memory_store = dcc.Store(id='data-memory-store')
clicks_store = dcc.Store(id='clicks-store', data=0)

title_row = dcc.Markdown('## Scale dependent correlation Analysis WebApp')

instructions_row = dcc.Markdown('Start by uploading a `.csv` file containing at the very least a'
                                ' single column with a column header and numerical values.',
                                style={'width': '800 px'})

ts1_dropdown = dcc.Dropdown(options=[{'label': 'Add dataset to select', 'value': 'Empty'}],
                            placeholder='Select time series 1', id='ts1-dropdown')
ts2_dropdown = dcc.Dropdown(options=[{'label': 'Add dataset to select', 'value': 'Empty'}],
                            placeholder='Select time series 2', id='ts2-dropdown')
date_dropdown = dcc.Dropdown(options=[{'label': 'Add dataset to select', 'value': 'Empty'}],
                            placeholder='Select time series 2', id='date-dropdown')
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
        style={**{
                'width': '500px',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px',
                'margin-left': '2 rem'
            }}
    ),
    html.Div(id='output-data-upload'),
])

run_button = html.Div(dbc.Button('Run SDC Analysis',
                      disabled=False,
                      style={'margin': '10px'},
                      id='run-button'),
                      id='run-button-div',
                      hidden=True)

results_div = html.Div(id='results-div')


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

@app.callback([Output('results-div', 'children'),
               Output('clicks-store', 'data')],
               Input('run-button', 'n_clicks'),
               Input('clicks-store', 'data'),
               Input('ts1-dropdown', 'value'),
               Input('ts2-dropdown', 'value'),
               Input('date-dropdown', 'value'),
               Input('method-dropdown', 'value'),
               Input('min-lag', 'value'),
               Input('max-lag', 'value'),
               Input('window', 'value'),
               Input('data-memory-store', 'data')
              )
def on_run_sdc_click(n_clicks, current_clicks, ts1, ts2, date, method, min_lag, max_lag, w, data):
    if n_clicks is not None and n_clicks > current_clicks:
        df = pd.DataFrame(data).assign(date=lambda dd: pd.to_datetime(dd[date])).set_index('date')
        computed_sdc = sdc.SDCAnalysis(ts1=df[ts1], ts2=df[ts2], method=method,
                                       min_lag=min_lag, max_lag=max_lag,
                                       fragment_size=w)
        buffer = io.BytesIO()
        computed_sdc.combi_plot(xlabel=ts1, ylabel=ts2, wspace=.3, hspace=.3, max_lag=max_lag,
                                min_lag=min_lag, figsize=(6, 6), title='')
        plt.savefig(buffer, format='png', dpi=150)
        plt.close()
        data = base64.b64encode(buffer.getbuffer()).decode("utf8")
        return [html.Img(src=f'data:image/png;base64,{data}')], n_clicks
    else:
        raise PreventUpdate

content_div = html.Div([title_row,
                        html.Hr(),
                        instructions_row,
                        file_upload,
                        parameter_rows,
                        html.Br(),
                        run_button,
                        html.Hr(),
                        results_div],
 style={'margin-left': '10rem', 'margin-right': '2rem', 'padding': '2rem 1rem'})

app.layout = html.Div(children=[sidebar,
                                content_div,
                                data_memory_store,
                                clicks_store])

app.title = 'SDCpy app'
if __name__ == '__main__':
    app.run_server(debug=True)
