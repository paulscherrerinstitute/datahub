import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import pandas as pd
from datahub import *
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd
import dash
#import dash_bootstrap_components as dbc
from dash import Dash, html, dcc, callback, Output, Input, State, dcc
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
backend = "sf-databuffer"
time_fmt = "%Y-%m-%d %H:%M:%S"
# Initialize the Dash app
app = dash.Dash(__name__)

# Dummy function to simulate receiving a dataset from a server
def get_dataset():
    source = Daqbuf(backend=backend, cbor=True, parallel=True, time_type="seconds")
    table = Table()
    source.add_listener(table)
    query = {"channels": ["S10BC01-DBPM010:Q1", "S10BC01-DBPM010:X1"],
         "start": (datetime.now() - timedelta(hours=1)).strftime(time_fmt),
         "end": datetime.now().strftime(time_fmt), "bins": 100}
    source.request(query)
    df = table.as_dataframe(Table.TIMESTAMP)
    if df is not None:
        df.reindex(sorted(df.columns), axis=1)
    return df


# Layout of the Dash app
app.layout = html.Div([
    dcc.Store(id='stored-data'),
    dcc.Dropdown(
        id="dropdown",
        options=[
            {"label": "Option 1", "value": "option1"},
            {"label": "Option 2", "value": "option2"}
        ],
        value="option1"
    ),
    html.Button('Load Data', id='load-data-button', n_clicks=0),
    html.Div(id="table-container")
])

# Callback to load data and store it in dcc.Store
@app.callback(
    Output('stored-data', 'data'),
    Input('load-data-button', 'n_clicks')
)
def load_data(n_clicks):
    if n_clicks > 0:
        dataset = get_dataset()
        return dataset.to_dict()
    return {}

# Callback to update the table based on dropdown selection
@app.callback(
    Output("table-container", "children"),
    [Input("dropdown", "value"), Input('stored-data', 'data')]
)
def update_table(selected_option, stored_data):
    if stored_data:
        dataset = pd.DataFrame(stored_data)
        if selected_option == "option1":
            return html.Table([
                html.Tr([html.Th(col) for col in dataset.columns]),
                html.Tr([html.Td(dataset.iloc[0][col]) for col in dataset.columns])
            ])
        else:
            return html.Table([
                html.Tr([html.Th(col) for col in dataset.columns]),
                html.Tr([html.Td(dataset.iloc[1][col]) for col in dataset.columns])
            ])
    return "No data loaded yet."

# Run the app
if __name__ == "__main__":
    app.run_server(debug=True)
