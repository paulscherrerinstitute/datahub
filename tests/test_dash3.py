from datahub import *
import pandas as pd
backend = "sf-databuffer"
channels = ["S10BC01-DBPM010:Q1", "S10BC01-DBPM010:X1"]
start = "2024-06-14 09:00:00"
end = "2024-06-14 10:00:00"
bins = None
df = None
query = None

def fetch_data(_bins):
    global df, bins, query
    bins = _bins
    query = {
        "channels": channels,
        "start": start,
        "end": end,
    }
    if (bins):
        query["bins"] = bins

    with Daqbuf(backend=backend, cbor=True, parallel=True, time_type="seconds") as source:
        table = Table()
        source.add_listener(table)
        source.request(query)
        #dataframe_cbor = table.as_dataframe(Table.PULSE_ID)
        df = table.as_dataframe(Table.TIMESTAMP)
        df.reindex(sorted(df.columns), axis=1)

fetch_data(100)

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash import Dash, html, dcc, callback, Output, Input, State
import plotly.graph_objects as go
import numpy as np


def get_figure(df, channel, color):
    cols = list(df.columns)
    binned = (channel + " max") in cols
    x= pd.to_datetime(df.index, unit='s')
    y=df[channel]
    return {
        'data': [
            go.Scatter(
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
                    array= df[channel + " max"] - y,
                    arrayminus= y - df[channel + " min"] ,
                    #array= [1.0] * len(df.index),
                    # arrayminus= [2.0] * len(df.index),
                    visible=True,
                    color=f'rgba({color[0]}, {color[1]}, {color[2]}, 0.1)'  # Set the color with transparency
                )
            )
        ],
        'layout': go.Layout(
            title=str(query),
            xaxis={'title': None},
            yaxis={'title': channel}
        )
    }

def fetch_graphs():
    return [
        dcc.Dropdown(channels, channels[0], id='dropdown-selection'),
        dcc.Graph(
            id='channel_graph',
            #figure= get_figure(df, channels[0], c)
        )
    ]


# Create the Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
c = (0 ,0, 255)
# Define the layout of the app
app.layout = html.Div(children=[
    html.H1(children='Daqbuf UI'),
    html.Div([
        html.Label('Bins:', style={'margin-right': '10px'}),
        dcc.Input(id='input_bins', type='number', min=0, max=1000, step=1, style={'margin-right': '10px'}, value=bins),
        html.Button('Submit', id='button')
    ], style={'display': 'flex', 'align-items': 'center', 'margin-bottom': '10px'}),
    html.Div(id='output-container', style={'margin-top': '20px'})
])




# Define the callback
@callback(
    Output('output-container', 'children'),
    Input('button', 'n_clicks'),
    State('input_bins', 'value')
)
def update_output(n_clicks, bins):
    if n_clicks is None:
        return ''
    fetch_data(bins)
    return fetch_graphs()



@callback(
    Output('channel_graph', 'figure'),
    Input('dropdown-selection', 'value')
)
def update_graph(value):
    return get_figure(df, value, c)

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
