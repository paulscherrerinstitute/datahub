import time
from datahub import *
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd
import dash
#import dash_bootstrap_components as dbc
from dash import Dash, html, dcc, callback, Output, Input, State, dcc
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
import numpy as np

backend = "sf-databuffer"
time_fmt = "%Y-%m-%d %H:%M:%S"
colors = [ (0 ,0, 255),  (255, 0, 0),  (0 ,255, 0), (0 ,127, 127),  (127, 127, 0),  (127 ,0, 127), (127 ,127, 127) ]


df = None
query = None
query = {"channels": ["S10BC01-DBPM010:Q1", "S10BC01-DBPM010:X1"],"start": (datetime.now() - timedelta(hours=1)).strftime(time_fmt),"end": datetime.now().strftime(time_fmt),"bins": 100}
number_queries = 0
source = Daqbuf(backend=backend, cbor=True, parallel=True, time_type="seconds")
table = Table()
source.add_listener(table)


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

def fetch_data(bins, channels, start, end):
    global df, query #, bins, channels, start, end
    query = {
        "channels": channels,
        "start": start,
        "end": end,
    }
    if (bins):
        query["bins"] = bins

    #with Daqbuf(backend=backend, cbor=True, parallel=True, time_type="seconds") as source:
    source.request(query)
    #dataframe_cbor = table.as_dataframe(Table.PULSE_ID)
    df = table.as_dataframe(Table.TIMESTAMP)
    if df is not None:
        df.reindex(sorted(df.columns), axis=1)


def get_series(df, channel, color, index):
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
        #yaxis = "y" if (index==0) else ("y"+str(index+1)),
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
            data.append(get_series(df, channel, colors[index % len(colors)], index))
            index+=1
    return {
        'data': data,
        'layout': go.Layout(
            #title=str(query),
            xaxis={'title': None},
            yaxis={'title': channels[0] if len(channels)==1 else None},
            margin=dict(t=40, b=40, l=80, r=40)  # Adjust the top margin (t) to make it smaller
        )
    }

def fetch_graphs(single):
    if single:
        return [
            dcc.Graph(id='graph', figure= get_figure(df, query["channels"]))
        ]
    else:
        return [
            dcc.Graph(
                id='graph_' + channel, figure=get_figure(df, [channel])
            ) for channel in query["channels"]
        ]



# Create the Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)

cmp_height = '30px'
label_style = {'margin-right': '0px', 'minHeight': cmp_height, 'display': 'flex', 'alignItems': 'center'}
input_style = {'margin-right': '10px', 'textAlign': 'center', 'minHeight': cmp_height}
check_style={'margin-right': '10px','minWidth': '80px', 'minHeight': cmp_height, 'display': 'flex', 'alignItems': 'center'}
drop_style = {'margin-right': '10px', 'min-width': '130px', 'minHeight': cmp_height}
range_options = ["Last 1min", "Last 10min", "Last 1h", "Last 12h", "Last 24h", "Last 7d", "Yesterday", "Today", "Last Week", "This Week", "Last Month", "This Month"]
# Define the layout of the app
app.layout = html.Div(children=[
    html.H1(children='Daqbuf UI'),
    html.Div([
        html.Label('Bins:', style=label_style),
        dcc.Input(id='input_bins', type='number', min=0, max=1000, step=1, style=input_style, value=100),
        html.Label('From:', style=label_style),
        dcc.Input(id='input_from', type='text', style=input_style, value=query["start"] if query else ""),
        html.Label('To:', style=label_style),
        dcc.Input(id='input_to', type='text', style=input_style, value=query["end"] if query else ""),
        dcc.Dropdown(id='dropdown_set_range', placeholder='Set time range', style=drop_style, options=range_options),
        html.Label('Channels:', style=label_style),
        dcc.Dropdown(id='dropdown_channels', placeholder='Enter query channel names', multi=True, value=query["channels"] if query else [], options=query["channels"] if query else [], style={'margin-right': '20px',  'minWidth': '100px', 'width':"100%", 'minHeight': cmp_height}),
        dcc.Checklist(id='checkbox_single',options=[{'label': 'Single', 'value': 'single'}], style=check_style),
        html.Button('Query', n_clicks=0, id='button_query', style={'minWidth': '100px', 'minHeight': cmp_height}),
        dcc.Loading(id="loading",type="default",children=html.Div(id='loading_output'))
    ], style={'display': 'flex', 'align-items': 'center', 'margin-bottom': '10px', 'justifyContent': 'center', }),
    html.Div(id='output-container', style={'margin-top': '20px'})
])

@app.callback(
    Output('input_from', 'value'),
    Output('input_to', 'value'),
    Input('dropdown_set_range', 'value')
)
def set_range(value):
    if not value:
        raise PreventUpdate
    now = datetime.now()
    start = None
    end = now

    if value == range_options[0]:
        start = now - timedelta(minutes=1)
    elif value == range_options[1]:
        start = now - timedelta(minutes=10)
    elif value == range_options[2]:
        start = now - timedelta(hours=1)
    elif value == range_options[3]:
        start = now - timedelta(hours=12)
    elif value == range_options[4]:
        start = now - timedelta(hours=24)
    elif value == range_options[5]:
        start = now - timedelta(days=7)
    elif value == range_options[6]:
        yesterday_date = now.date() - timedelta(days=1)
        start = datetime.combine(yesterday_date, datetime.min.time())
        end = datetime.combine(yesterday_date, datetime.max.time())
    elif value == range_options[7]:
        start = datetime.combine(now.date(), datetime.min.time())
    elif value == range_options[8]:
        start_of_current_week = now.date() - timedelta(days=now.weekday())
        end_of_last_week = start_of_current_week - timedelta(days=1)
        start_of_last_week = end_of_last_week - timedelta(days=6)
        start = datetime.combine(start_of_last_week, datetime.min.time())
        end = datetime.combine(end_of_last_week, datetime.max.time())
    elif value == range_options[9]:
        start = datetime.combine(now.date() - timedelta(days=now.weekday()), datetime.min.time())
    elif value == range_options[10]:
        previous_month = now - relativedelta(months=1)
        first_day_of_previous_month = previous_month.replace(day=1)
        last_day_of_previous_month = previous_month.replace(day=1) + relativedelta(months=1) - timedelta(days=1)
        start = datetime.combine(first_day_of_previous_month, datetime.min.time())
        end = datetime.combine(last_day_of_previous_month, datetime.max.time())
    elif value == range_options[11]:
        first_day_of_current_month = now.replace(day=1)
        start = datetime.combine(first_day_of_current_month, datetime.min.time())
    start = start.strftime(time_fmt)
    end = end.strftime(time_fmt)
    return start, end



@callback(
    Output('button_query', 'disabled', allow_duplicate=True),
    Input('button_query', 'n_clicks'),
    prevent_initial_call=True
)
def on_click(n_clicks):
    if not n_clicks:
        raise PreventUpdate
    return True

@callback(
    Output('output-container', 'children'),
    Output('loading_output', 'children'),
    Output('button_query', 'disabled', allow_duplicate=True),
    Input('button_query', 'n_clicks'),
    Input('checkbox_single', 'value'),
    State('input_bins', 'value'),
    State('dropdown_channels', 'value'),
    State('input_from', 'value'),
    State('input_to', 'value'),
    State('checkbox_single', 'value'),
    prevent_initial_call=True
)
def update_data(n_clicks, _, bins, channels, start, end, single):
    global number_queries
    if not n_clicks:
        raise PreventUpdate
    query = False
    if number_queries != n_clicks:
        if source.is_running():
            raise PreventUpdate
        number_queries = n_clicks
        query = True
    if len(channels)==0:
        return '','', False
    #channels = [item.strip() for item in chaneels.split(',')]
    if query:
        _start = time.time()
        fetch_data(bins, channels, start, end)

    return fetch_graphs(single[0] if single else None), '', False

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
