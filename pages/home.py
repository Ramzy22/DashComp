import dash
from dash import html, dcc
import dash_mantine_components as dmc
import pandas as pd
import dash_ag_grid as dag
from dash_iconify import DashIconify
import requests
import zipfile
import io
import datetime
from twisted.runner.procmon import transport

# Load the data from the uploaded files
data_dict_path = r'C:\Users\ramzy\PycharmProjects\dashComp\MTA_data_dictionary.csv'
ridership_path = r'C:\Users\ramzy\PycharmProjects\dashComp\MTA_Daily_Ridership.csv'

# Read the CSV files into pandas DataFrames
data_dict_df = pd.read_csv(data_dict_path)
ridership_df = pd.read_csv(ridership_path)
ridership_df["Date"]=pd.to_datetime(ridership_df["Date"])
# Display the first few rows of each to understand their structure
data_dict_df.head(), ridership_df.head()

# Map categories to DashIconify components for Segmented Control
icon_mapping = {
    "Subways": DashIconify(icon="mdi:subway-variant", width=30, height=30, color="#0072B2"),  # Blue
    "Buses": DashIconify(icon="mdi:bus", width=30, height=30, color="#E69F00"),  # Orange
    "LIRR": DashIconify(icon="mdi:train", width=30, height=30, color="#009E73"),  # Green
    "Metro-North": DashIconify(icon="mdi:train-car", width=30, height=30, color="#56B4E9"),  # Light Blue
    "Access-A-Ride": DashIconify(icon="mdi:wheelchair-accessibility", width=30, height=30, color="#CC79A7"),  # Pink
    "Bridges and Tunnels": DashIconify(icon="mdi:bridge", width=30, height=30, color="#F0E442"),  # Yellow
    "Staten Island Railway": DashIconify(icon="mdi:tram", width=30, height=30, color="#D55E00")  # Red
}

icon_mapping_color = {
    "Subways": "#0072B2",  # Blue
    "Buses": "#E69F00",  # Orange
    "LIRR": "#009E73",  # Green
    "Metro-North": "#56B4E9",  # Light Blue
    "Access-A-Ride": "#CC79A7",  # Pink
    "Bridges and Tunnels": "#F0E442",  # Yellow
    "Staten Island Railway": "#D55E00",  # Red
    "Other" : "grey"
}

# Download GTFS data
def fetch_gtfs_data(url):
    response = requests.get(url)
    if response.status_code == 200:
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            with z.open("stops.txt") as f:
                stops_df = pd.read_csv(f)
        return stops_df
    else:
        raise Exception(f"Failed to download GTFS data from {url}")

# Fetch data for different categories
def fetch_all_data():
    urls = {
        "Subways": "http://web.mta.info/developers/data/nyct/subway/google_transit.zip",
        "Buses": "http://web.mta.info/developers/data/bus/google_transit_bronx.zip",
        "LIRR": "http://web.mta.info/developers/data/lirr/google_transit.zip",
        "Metro-North": "http://web.mta.info/developers/data/mnr/google_transit.zip",
        "Staten Island Railway": "http://web.mta.info/developers/data/nyct/subway/google_transit.zip",  # Same GTFS as Subways
        "Bridges and Tunnels": "unknown",
        "Access-A-Ride": "unknown"
    }

    data = {}
    for category, url in urls.items():
        print(f"Fetching {category} data...")
        try:

            stops = fetch_gtfs_data(url)
            # Filter for unique stops with coordinates
            stops = stops[["stop_id", "stop_name", "stop_lat", "stop_lon"]].drop_duplicates()
            stops["Category"] = category
            data[category] = stops
        except Exception as e :
            stops = pd.DataFrame([["Not Found", "0", 40.7128, -74.0060]],
                                columns=["stop_id", "stop_name", "stop_lat", "stop_lon"])
            stops["Category"] = category
            data[category] = stops
            data[category] = stops
            print(e)
            pass

    return pd.concat(data.values(), ignore_index=True)

# Fetch Bridges and Tunnels data
def fetch_bridges_and_tunnels():
    url = "https://data.cityofnewyork.us/resource/6u9h-4k42.csv"
    response = requests.get(url)

    if response.status_code == 200:
        # Read the CSV content into a DataFrame
        data = pd.read_csv(io.StringIO(response.text))
        return data
    else:

        raise Exception("Failed to download Bridge and Tunnel data")


# Combine all data
try:
    transportation_data = fetch_all_data()
    #bridges_tunnels_data = fetch_bridges_and_tunnels()
    full_data = transportation_data#pd.concat([transportation_data, bridges_tunnels_data], ignore_index=True)
    full_data.to_csv(r"C:\Users\ramzy\PycharmProjects\dashComp\data_local.csv")
except Exception as e:
    print(e)
# Map column names to their descriptions
tooltips = dict(zip(data_dict_df['Field'], data_dict_df['Description']))

# Group the ridership columns by category
column_groups = {}

for i in ridership_df.columns:
    if(":" in i):
        x = i.split(":")
        if x[0] in column_groups.keys():
            column_groups[x[0]].append(i)
        else:
            column_groups[x[0]] = [i]
# Configure the column definitions for AG Grid with tooltips
column_defs = [
    {
        "headerName": col,
        "field": col,
        "tooltipField": col,  # Link tooltip to column
        "tooltipComponentParams": {
            "value": tooltips.get(col, "No description available"),
        },
    }
    for col in ridership_df.columns
]

# Segmented Control for Category Selection
data=[
        {"value": category, "label": dmc.Center(
            children=[icon_mapping[category], html.Span(category)],
            style={"gap": 10},
        )}
        for category in column_groups.keys()
    ]
data=[{"value": "All", "label":dmc.Center(
            children=[DashIconify(icon="mdi:select-all", width=30, height=30), html.Span("All")],
            style={"gap": 10})}]+data
segmented_control = dmc.SegmentedControl(
    id="column-segmented-control",
    value="All",  # Default selection
    data=data,
    fullWidth=True
)

# Interval for automatic updates (1 day per second)
inter=    dcc.Interval(
        id='interval-update',
        interval=1500,  # 1000 ms = 1 second per day
        n_intervals=0,
        disabled=True  # Initially disabled (paused)
    )
graph=dcc.Graph(id='nyc-map') # Animated map visualization
slider=  dmc.Slider(
            id='day-slider',
            value=0,
            marks=[{"value" : i ,"label" :str(date.date()) }for i, date in enumerate(ridership_df['Date']) if i%365==0],
            max=len(ridership_df),
            mb=35,
        )


# Layout Definition
layout = html.Div([

    slider,

    dmc.Space(h=20),
    segmented_control,
    dmc.Space(h=20),  # Adds spacing
    inter,
    # Play/Pause Button
    dmc.Accordion(
            multiple=True,
            variant="separated",
            # Bar Graph Section
            children=[

                dmc.AccordionItem([
                    dmc.AccordionControl(
                        [
                            DashIconify(icon="mdi:chart-line", width=20, style={'marginRight': '10px'}),
                            # Line Graph Icon
                            dmc.Text("Timeline")
                        ]),
                    dmc.AccordionPanel([dmc.Switch(
                                        size="lg",
                                        radius="sm",
                                        label="Percentage",
                                        checked=False,
                                        id="Percentage_switch"
                                    ),dmc.Space(),dcc.Graph(id="data-graph")])

                ],
                    value="Line",

                ),
            # Map Graph Section
            dmc.AccordionItem([
                dmc.AccordionControl(
                    [
                        DashIconify(icon="mdi:map", width=20, style={'marginRight': '10px'}),  # Map Graph Icon
                    dmc.Text("Spacial Visualization") ]),
                dmc.AccordionPanel(graph)],
                value="Map",


            ),
                dmc.AccordionItem(
                    [
                        dmc.AccordionControl([
                            DashIconify(icon="mdi:chart-bar", width=20, style={'marginRight': '10px'}),
                            # Bar Graph Icon
                            dmc.Text("Bar Graph")
                        ]),
                        dmc.AccordionPanel(dcc.Graph(id='category-bar'))
                    ],
                    value="Bar",

                ),
            # Line Graph Section

        ]
    ),
    dmc.Space(h=20),
    dag.AgGrid(
        id="grid",
        rowData=ridership_df.to_dict("records"),  # Convert DataFrame to list of dictionaries
        columnDefs=column_defs,
        defaultColDef={
            "tooltipComponent": "agTooltipComponent",
            "sortable": True,
            "filter": True,
            "resizable": True,
        },
        dashGridOptions={
            "pagination": True,
            "paginationPageSize": 10,
        },
        columnSize="responsiveSizeToFit",
        className="ag-theme-alpine-dark",  # Default theme
        style={"height": "500px", "width": "100%"},
    ),
])
