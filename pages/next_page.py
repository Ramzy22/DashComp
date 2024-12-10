import dash
from dash import html
import dash_mantine_components as dmc


layout = html.Div([
    html.H1("Page 2"),
    dmc.NavLink("Go to Page 1", href="/")
])
