import dash
from dash import dcc, html, Output, Input

app = dash.Dash(__name__)

app.layout = html.Div([
    dcc.Store(id='page-load-event'),
    html.Div(id='output')
])

# Client-side callback to trigger on page load
app.clientside_callback(
    """
    function(n_intervals) {
        return n_intervals;
    }
    """,
    Output('page-load-event', 'data'),
    Input('interval', 'n_intervals'),
    prevent_initial_call=False
)

# Interval component to trigger the client-side callback
app.layout.children.append(dcc.Interval(id='interval', interval=1, n_intervals=0))

if __name__ == '__main__':
    app.run_server(debug=True)
