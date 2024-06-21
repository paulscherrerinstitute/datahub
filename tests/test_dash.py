from datahub import *
from datetime import date, datetime, timedelta
import pandas as pd
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash import Dash, html, dcc, callback, Output, Input, State
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
import numpy as np


now = datetime.now()

time_fmt = "%Y-%m-%d %H:%M:%S"
backend = "sf-databuffer"
channels = "S10BC01-DBPM010:Q1", "S10BC01-DBPM010:X1"
start = (now - timedelta(hours=1)).strftime(time_fmt)
end = now.strftime(time_fmt)
bins = 100
df = None
query = None
colors = [ (0 ,0, 255),  (255, 0, 0),  (0 ,255, 0), (0 ,127, 127),  (127, 127, 0),  (127 ,0, 127), (127 ,127, 127) ]

source = Daqbuf(backend=backend, cbor=True, parallel=True, time_type="seconds")

def search_channels(regex):
    if not regex:
        return []
    #with Daqbuf(backend=backend) as source:
    source.verbose = True
    try:
        ret = source.search(regex)
        results = [ch["name"] for ch in  ret.get("channels", [])]
    except:
        results = []

    return [{'label': result, 'value': result} for result in results]

def fetch_data(_bins, _channels, _start, _end):
    global df, bins, query, channels, start, end
    bins = _bins
    channels = _channels
    start = _start
    end = _end
    query = {
        "channels": channels,
        "start": start,
        "end": end,
    }
    if (bins):
        query["bins"] = bins

    #with Daqbuf(backend=backend, cbor=True, parallel=True, time_type="seconds") as source:
    table = Table()
    source.add_listener(table)
    source.request(query)
    #dataframe_cbor = table.as_dataframe(Table.PULSE_ID)
    df = table.as_dataframe(Table.TIMESTAMP)
    if df is not None:
        df.reindex(sorted(df.columns), axis=1)

#fetch_data(100, ["S10BC01-DBPM010:Q1", "S10BC01-DBPM010:X1"], "2024-06-14 09:00:00", "2024-06-14 10:00:00")

def get_series(df, channel, color):
    cols = list(df.columns)
    binned = (channel + " max") in cols
    x = pd.to_datetime(df.index, unit='s')
    y = df[channel]

    return go.Scatter(
        x=x,
        y=y,
        mode='lines+markers',
        name=channel,
        line=dict(color=f'rgba({color[0]}, {color[1]}, {color[2]}, 1.0)'),
        marker=dict(
            color=f'rgba({color[0]}, {color[1]}, {color[2]}, 1.0)',
            size=5
        ),
        error_y=None if not binned else dict(
            type='data',
            symmetric=False,
            array=df[channel + " max"] - y,
            arrayminus=y - df[channel + " min"],
            # array= [1.0] * len(df.index),
            # arrayminus= [2.0] * len(df.index),
            visible=True,
            color=f'rgba({color[0]}, {color[1]}, {color[2]}, 0.1)'  # Set the color with transparency
        )
    )


def get_figure(df, channels):
    if (df is None) or (channels is None) :
        return {}
    data = []
    index = 0
    for channel in channels:
        if (channel in df.columns):
            data.append(get_series(df, channel, colors[index % len(colors)]))
            index+=1
    return {
        'data': data,
        'layout': go.Layout(
            #title=str(query),
            xaxis={'title': None},
            yaxis={'title': channel},
            margin=dict(t=40, b=40, l=80, r=40)  # Adjust the top margin (t) to make it smaller
        )
    }

def fetch_graphs(single):
    if single:
        return [
            dcc.Graph(id='graph', figure= get_figure(df, channels))
        ]
    else:
        return [
            dcc.Graph(
                id='graph_' + channel, figure=get_figure(df, [channel])
            ) for channel in channels
        ]



# Create the Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)

# Define the layout of the app
app.layout = html.Div(children=[
    html.H1(children='Daqbuf UI'),
    html.Div([
        html.Label('Bins:', style={'margin-right': '10px'}),
        dcc.Input(id='input_bins', type='number', min=0, max=1000, step=1, style={'margin-right': '20px', 'textAlign': 'center'}, value=bins),
        html.Label('From:', style={'margin-right': '10px'}),
        dcc.Input(id='input_from', type='text', style={'margin-right': '10px', 'textAlign': 'center'}, value=str(start)),
        html.Label('To:', style={'margin-right': '10px'}),
        dcc.Input(id='input_to', type='text', style={'margin-right': '10px', 'textAlign': 'center'}, value=str(end)),
        html.Label('Channels:', style={'margin-right': '10px'}),
        dcc.Dropdown(id='dropdown_channels', placeholder='Enter query channel names', multi=True, value=channels, options=channels, style={'margin-right': '10px',  'minWidth': '100px', 'width':"100%"}),
        dcc.Checklist(id='checkbox_single',options=[{'label': 'Single', 'value': 'single'}], style={'margin-right': '10px','minWidth': '100px'}),
        html.Button('Query', id='button'),
    ], style={'display': 'flex', 'align-items': 'center', 'margin-bottom': '10px'}),
    html.Div(id='output-container', style={'margin-top': '20px'})
])



# Define the callback
@callback(
    Output('output-container', 'children'),
    Input('button', 'n_clicks'),
    Input('checkbox_single', 'value'),
    State('input_bins', 'value'),
    State('dropdown_channels', 'value'),
    State('input_from', 'value'),
    State('input_to', 'value'),
    State('checkbox_single', 'value')
)
def update_data(n_clicks, _, bins, channels, start, end, single):
    if n_clicks is None:
        return ''
    if len(channels)==0:
        return ''
    #channels = [item.strip() for item in chaneels.split(',')]
    fetch_data(bins, channels, start, end)
    return fetch_graphs(single[0] if single else None)

@app.callback(
    Output('dropdown_channels', 'options'),
    Input('dropdown_channels', 'search_value'),
    State("dropdown_channels", "value")
)
def update_results(regex, value):
    if not regex or len(regex)<3:
        raise PreventUpdate
    options = search_channels(regex)
    #return [o for o in options if o not in value]
    #Must add to options or else selected value will be removed
    if value:
        options = options + [{'label': V, 'value': V} for V in value]
    return options



# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
