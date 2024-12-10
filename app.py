import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import Dash, Input, Output, State, callback, _dash_renderer, html, dcc, register_page
from pages import home, next_page
import plotly.express as px
import pandas as pd
import dash
_dash_renderer._set_react_version("18.2.0")
import plotly.graph_objs as go
import time
import numpy as np
import openai
app = Dash(__name__, external_stylesheets=dmc.styles.ALL,suppress_callback_exceptions=True, prevent_initial_callbacks='initial_duplicate')
template =  "plotly_dark"
register_page(__name__, path="/next_page")
register_page(__name__, path="/")

theme_toggle =dmc.Switch(
    onLabel=DashIconify(icon="radix-icons:moon", width=20),
    offLabel=DashIconify(icon="radix-icons:sun", width=20),
    size="xl",
    id="color-scheme-toggle",
    checked=True
)

left_side= dmc.Center([dmc.Space("l"),dmc.DatesProvider(
                children=dmc.Stack(
                    [
                        dmc.Center([
                        dmc.DatePickerInput(
                            w=250,
                            label="Choose a date",
                            id="date-picker-input",
                            minDate=home.ridership_df.Date.iloc[0],
                            maxDate=home.ridership_df.Date.iloc[-1],

                        ),]),  dmc.Space(h="l"),
                             html.Button(id='play-pause-btn', n_clicks=0, children="Play",
                                         style={"font-size": "20px", "margin": "20px"}),
                        dmc.Center([dmc.Stack(    align="center",
                            children=[

                            dmc.Group(
                            children=[
                                dmc.PasswordInput(
                                    id="api-key-input",
                                    label="Enter OpenAI API Key",
                                    placeholder="sk-...",
                                    style={"width": "60%"}
                                ),
                                dmc.Button("Submit Key", id="submit-key", color="blue"),
                            ],
                            ),
                        html.Div(id="key-status", style={"marginTop": "10px", "textAlign": "center"}),

                        # Chat Interface
                        dmc.Group(
                            children=[
                                dmc.TextInput(
                                    id="user-query",
                                    label="Ask a question about the data, (day and category need to be precised in the prompt)",
                                    placeholder="e.g., On the 7th of august what was the subways level compared to pre covid",
                                    style={"margin-left":"3vh","margin-right":"3vh"},
                                ),]),
                                dmc.Button("Ask ChatGPT", id="submit-query", color="green"),


                        html.Div(id="query-response", style={"marginTop": "20px", "textAlign": "center"}),
                        ]),]),
                        # Hidden Div to Store API Key
                        dcc.Store(id="api-key-store"),

                             ]
                ),
                settings={"locale": "us", "firstDayOfWeek": 0, "weekendDays": [0]},

            )])# OpenAI API Key Input


navbar = dmc.AppShellNavbar(
    p="md",
    children=[
        dmc.Group(
            children=[
                dmc.NavLink(href="/",
                            leftSection=DashIconify(icon="tabler:gauge"),
                            rightSection=DashIconify(icon="tabler-chevron-right"),
                            color="orange",
                            variant="filled",
                            label="With right section",
                            active=True,
                            ),
                dmc.NavLink( href="/next_page",    color="orange",
                             variant="dark",
                             label="With right section",
                             active=True,
                             leftSection=DashIconify(icon="tabler:gauge"),
                            rightSection=DashIconify(icon="tabler-chevron-right")),
            ]
        )
    ]
)

title=dmc.Group(  # Use a Group to style the header
    children=[theme_toggle,
        dmc.Title("NYC MTA Ridership and Geographic Visualization", size="h1")
    ],
    style={"marginTop": "20px", "marginBottom": "20px","position":"center"}
),
appshell=dmc.AppShell(
    [
        dmc.AppShellHeader(dmc.Center(title), px=25),
        dmc.AppShellNavbar(left_side
    ),
        dmc.AppShellAside(None,darkHidden=True,lightHidden=True),
        dmc.AppShellMain(children=[dcc.Location(id='url', refresh=False),html.Div(id='page-content')]),
    ],
    header={"height": 70},
    padding="xl",
    navbar={
        "width": 300,
        "breakpoint": "sm",
        "collapsed": {"mobile": True},
    },
    aside={
        "width": 0,
        "breakpoint": "xl",
        "collapsed": {"desktop": False, "mobile": True},
    },
)
app.layout = dmc.MantineProvider(
    children=[appshell]
    ,
    id="mantine-provider",
    forceColorScheme="dark",
)

# Store API Key and validate
@app.callback(
    Output("api-key-store", "data"),
    Output("key-status", "children"),
    Output("key-status", "style"),
    Input("submit-key", "n_clicks"),
    State("api-key-input", "value"),
    prevent_initial_call=True
)
def store_api_key(n_clicks, key):
    if not key:
        return dash.no_update, "API key cannot be empty!", {"color": "red"}

    # Test the API key by making a small query
    try:
        openai.api_key = key
        openai.Engine.list()  # This will throw an error if the key is invalid
        return key, "API key validated successfully!", {"color": "green"}
    except Exception as e:
        return None, "Invalid API key. Please try again.", {"color": "red"}


# Process query using ChatGPT
@app.callback(
    Output("query-response", "children"),
    Input("submit-query", "n_clicks"),
    State("api-key-store", "data"),
    State("user-query", "value"),
    prevent_initial_call=True
)
def answer_query(n_clicks, api_key, query):
    if not api_key:
        return "Please provide a valid API key first."

    if not query:
        return "Query cannot be empty."

    # Construct prompt with DataFrame content
    dataframe_text = home.ridership_df.to_string(index=False)
    prompt = f"""
    Here is a DataFrame:
    {dataframe_text}

    Question: {query}

    Provide a concise answer.
    """

    try:
        # Set the API key
        openai.api_key = api_key

        # Generate response using ChatGPT
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are an expert data analyst."},
                      {"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Error: {str(e)}"

# Callback to toggle theme
@app.callback(
    Output("mantine-provider", "forceColorScheme"),
    Output("grid", "className"),
    Input("color-scheme-toggle", "checked"),
    State("mantine-provider", "forceColorScheme"),

)
def toggle_theme(is_dark_mode,theme):
    # Set the Mantine theme
    theme = "dark" if is_dark_mode else "light"
    # Set AG Grid theme
    ag_grid_theme = "ag-theme-alpine-dark" if is_dark_mode else "ag-theme-alpine"

    return theme, ag_grid_theme



@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    if pathname == '/':
        return home.layout
    elif pathname == '/next_page':
        return next_page.layout
    else:
        return '404 Page Not Found'


"""
# Callback to update the table based on the selected column
@app.callback(
    Output("grid", "columnDefs"),
    Input("column-segmented-control", "value"),
    prevent_initial_call = True,
)
def update_table(selected_column):
    x= home.column_groups[selected_column]
    print(x)
    updated_column_defs = [
        {
            "headerName": col,
            "field": col,
            "tooltipField": col,
            "tooltipComponentParams": {
                "value": home.tooltips.get(col, "No description available"),
            },
            "hide": col != "Date" and not(col in x),  # Show only the selected column and Date
        }
        for col in home.ridership_df.columns
    ]
    return updated_column_defs
"""


@app.callback(
    Output("grid", "columnDefs"),
    Output("grid", "rowData"),
    Output("grid", "dashGridOptions"),
    Input("column-segmented-control", "value")
)
def update_ag_grid(selected_columns):
    # Always include the 'Date' column
    if(selected_columns !="All"):
        columns_to_display = ["Date"] + (home.column_groups[selected_columns] or [])
    else:
        columns_to_display=home.ridership_df.columns
    # Generate column definitions for the selected columns
    column_defs = [{"headerName": col, "field": col, "sortable": True, "filter": True} for col in columns_to_display]
    options_for_resize={
        "pagination": True,
        "paginationPageSize": 10,
    }
    try:
        # Filter the data to include only the selected columns
        if(selected_columns !="All"):
            filtered_data = home.ridership_df[columns_to_display].to_dict("records")
        else:
            filtered_data = home.ridership_df.loc[columns_to_display].to_dict("records")
    except:
        filtered_data=home.ridership_df.to_dict("records")
    return column_defs, filtered_data, options_for_resize




@app.callback(
    Output('nyc-map', 'figure'),
    Output('category-bar', 'figure'),
    Output("data-graph", "figure"),

    [Input('day-slider', 'value'),
     Input("column-segmented-control", "value"),
     Input("Percentage_switch", "checked"),
    Input("color-scheme-toggle","checked")
     ]
)
def update_map(selected_day,selected_category,switch,theme):
    # Filter data for the selected day
    template="plotly_white"
    if(theme):
        template="plotly_dark"
    current_data = home.ridership_df.iloc[int(selected_day)]
    current_date = current_data["Date"]
    filtered_data = home.full_data.copy()
    filtered_data["Date"]=current_date
    filtered_data["Percentage"]=filtered_data.Category.apply(lambda x : current_data[home.column_groups[x][1]]/8)

    # Apply opacity based on the selected category

    filtered_data["opacity"] = filtered_data["Category"].apply(
        lambda x: 1 if (x == selected_category or selected_category=="All") else 0.005
    )
    filtered_data["color"] = filtered_data["Category"].apply(
        lambda x:home.icon_mapping_color[x]
    )

    # Plot data with Plotly
    fig = px.scatter_mapbox(
        filtered_data,
        template=template,
        lat="stop_lat",
        lon="stop_lon",
        hover_name="stop_name",
        hover_data={"Percentage": True, "Category": True, "Date": True},
        title=f"Transportation Activity on {current_date.date()}",
        mapbox_style="carto-positron",
        size_max=6,  # Increase max size for large percentages
    )

    # Apply opacity and colors based on selected category
    fig.update_traces(
        marker=dict(
            opacity=filtered_data["opacity"],  # Apply opacity based on category selection
            size=filtered_data["Percentage"],
            color=filtered_data["color"],  # Color by transportation category
        )
    )

    # -------------------- Bar graph (go.Figure) --------------------

    # Group the data by Category and calculate the total ridership (Percentage)
    category_data = filtered_data.groupby('Category')['Percentage'].first().reset_index()

    all_categories = set(home.icon_mapping.keys())
    current_categories = set(category_data['Category'])

    # Find missing categories
    missing_categories = all_categories - current_categories

    # Create rows for missing categories with Percentage=0
    if missing_categories:
        missing_data = pd.DataFrame({
            'Category': list(missing_categories),
            'Percentage': [0] * len(missing_categories)
        })
        # Concatenate the missing rows to category_data
        category_data = pd.concat([category_data, missing_data], ignore_index=True)

    # Ensure the final DataFrame has the correct order
    category_data = category_data.sort_values('Category').reset_index(drop=True)
    # Create the bar chart for the selected date
    bar_fig = go.Figure(   layout=dict(
        barcornerradius=10,
    ),)
    category_data['Percentage']=category_data['Percentage']*8


    for category in category_data['Category']:
        bar_fig.add_trace(go.Bar(

            x=[category],  # Single category at a time
            y=category_data.loc[category_data['Category'] == category, 'Percentage'],
            name=category,  # Use the category name for the legend
            marker=dict(color=home.icon_mapping_color[category]),
            opacity=1 if (category == selected_category or selected_category=="All") else 0.3  # Highlight selected category
        ))
    # Add a horizontal line at y=1
    bar_fig.add_shape(
        type="line",
        x0=-0.5,  # Adjust to ensure it spans across all categories
        x1=len(category_data['Category']) - 0.5,  # Adjust for the number of bars
        y0=100,
        y1=100,
        line=dict(color="grey", width=2, dash="dash"),  # Custom line style
    )

    # Add annotation for the line
    bar_fig.add_annotation(
        x=len(category_data['Category']) - 1,  # Place the text at the end of the line
        y=100,  # Align with the line's y-coordinate
        text="Reference Value Pre-COVID",  # Annotation text
        showarrow=False,
        font=dict(size=8, color="red"),  # Customize font style
        align="center",
        xanchor="left",  # Align text with the line
        yanchor="bottom",
    )
    # Set the layout for the bar graph
    bar_fig.update_layout(
        title=f"Ridership Activity on {current_date.date()}",
        template=template,
        xaxis_title="Category",
        yaxis_title="Total Ridership (Percentage)",
        xaxis=dict(
            tickmode='array',
            tickvals=category_data['Category'],  # Ensure all categories are displayed on x-axis
            ticktext=category_data['Category'],  # Display category names
            showgrid=False,
            categoryorder="array",  # Enforce a specific order
            categoryarray=np.array(list(home.icon_mapping.keys())),  # Your custom array for the x-axis
        ),
        yaxis=dict(
            range=[0, 150  ],  # Set the fixed range for the y-axis between 0 and 1.5
            showgrid=False,

        ),
        barmode='stack',
        showlegend=True,
        transition_duration=1500  # Smooth transition with 500ms duration
    )
    # -------------------- Line Graph --------------------
    # Update cumulative data
    cumulative_df= home.ridership_df.iloc[:selected_day]
    line_fig = go.Figure( )
    index=1 if switch else 0
    strl="in % Percentage estimated pre covid" if switch else "Total Estimated"
    for col in home.column_groups.keys():  # Replace with actual columns
        column=home.column_groups[col][index]
        line_fig.add_trace(go.Scatter(
            x=cumulative_df['Date'],
            y=cumulative_df[column],
            mode='lines',
            name=column,
            opacity=1 if (col == selected_category or selected_category=="All") else 0.3,  # Dynamic opacity
            line=dict(width=2 if (column == selected_category or selected_category=="All") else 1)  # Highlight the selected line
        ))

    line_fig.update_layout(
        template=template,
        xaxis_title="Date",
        yaxis_title="Ridership" + strl ,
        xaxis=dict(showgrid=True),
        showlegend=True,

    )
    return fig, bar_fig, line_fig



@callback(
    Output("play-pause-btn", "n_clicks",allow_duplicate=True),

    Output("day-slider", "value",allow_duplicate=True),

   Input("date-picker-input", "value"),
    State("play-pause-btn", "n_clicks"),


    prevent_initial_call = True,
)
def update_output(d,n_clicks):
    d=pd.to_datetime(d)
    x=d-home.ridership_df.Date.iloc[0]
    return 1,    x.days
# Update the slider value with each interval
@app.callback(
    Output('day-slider', 'value'),
    [Input('interval-update', 'n_intervals')],
    [State('day-slider', 'value')],
)
def update_slider(n_intervals, current_value):
    next_day = (current_value + 30) % len(home.ridership_df)
    return next_day

# Toggle play/pause for the interval
@app.callback(
    Output('interval-update', 'disabled'),
    [Input('play-pause-btn', 'n_clicks')],
    [State('interval-update', 'disabled')]
)
def toggle_interval(n_clicks, current_state):
    # Toggle the disabled state of the interval
    if n_clicks % 2 == 0:
        return False  # Play: Enable interval
    else:
        return True  # Pause: Disable interval

# Update play/pause button text
@app.callback(
    Output('play-pause-btn', 'children'),
    [Input('play-pause-btn', 'n_clicks')]
)
def update_button_text(n_clicks):
    if n_clicks % 2 == 0:
        return "Pause"
    else:
        return "Play"



if __name__ == "__main__":
    app.run(debug=True)













