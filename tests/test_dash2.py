import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import numpy as np

# Generate example data
x = np.linspace(0, 10, 500)
y = np.sin(x)
y_upper_error = 0.1 + 0.2 * np.sqrt(x)
y_lower_error = 0.1 + 0.1 * np.sqrt(x)

# Create the Dash app
app = dash.Dash(__name__)
c = (0 ,0, 255)
# Define the layout of the app
app.layout = html.Div(children=[
    html.H1(children='Line Plot with Error Bars'),

    dcc.Graph(
        id='line-error-plot',
        figure={
            'data': [
                go.Scatter(
                    x=x,
                    y=y,
                    mode='lines+markers',
                    name='Data',
                    line=dict(color=f'rgba({c[0]}, {c[1]}, {c[2]}, 1.0)'),
                    marker=dict(
                        color=f'rgba({c[0]}, {c[1]}, {c[2]}, 1.0)',
                        size=5
                    ),
                    error_y=dict(
                        type='data',
                        symmetric=False,
                        array=y_upper_error,
                        arrayminus=y_lower_error,
                        visible=True,
                        color=f'rgba({c[0]}, {c[1]}, {c[2]}, 0.1)'  # Set the color with transparency
                    )
                )
            ],
            'layout': go.Layout(
                title='Line Plot with Asymmetric Error Bars and Transparency',
                xaxis={'title': 'X Axis'},
                yaxis={'title': 'Y Axis'}
            )
        }
    )
])

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
