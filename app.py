# -*- coding: utf-8 -*-
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from urllib.request import urlopen
import json
with urlopen('https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json') as response:
    counties = json.load(response)


app = dash.Dash(__name__)

server = app.server

cdf = pd.read_csv('data/by_county_epa_df.csv',index_col=0, converters={'fips': lambda x: str(x)})
# change to proper types for leading zeros
cdf['fips'] = [i.zfill(5) for i in cdf['fips']]

edf = pd.read_csv('data/epa_df_counties.csv',index_col=0)
#read in AQI classification df
aqi_c = pd.read_csv("data/aqi_table_classifications.csv")
aqi_class = aqi_c.iloc[:,-3:]
aqi_class.drop(aqi_class.index[0],inplace=True)
aqi_class[['AQI',"AQI.1"]] = aqi_class[['AQI',"AQI.1"]].astype(int)

states = np.sort(cdf['state_abv'].unique())
# states = np.insert(states,0,"USA",axis=0)
years = cdf['year'].unique()
app.layout = html.Div(children=[
                      html.Div(className='row',  # Define the row element
                               children=[
                                  html.Div(className='four columns div-user-controls',
                                      children = [
                                          html.H2('Air Quality Index Dashboard'),
                                          html.P('''Visualising Timeseries Pollution Data with Plotly - Dash'''),
                                          html.Div(className="div-for-dropdown",
                                          children=[
                                            dcc.Dropdown(id='state', options=[{'label': i, 'value': i} for i in states],
                                                       style={'width': '140px'}, placeholder="Select State"),
                                            html.Div(id='div-for-pollutant-state',
                                                children =[
                                                    dcc.Dropdown(id='county_select',style={'width': '140px'},
                                                    placeholder='Select County'),
                                                    dcc.Dropdown(id = 'pollutant_select',style={'width': '140px'},placeholder="Select Pollutant",
                                                                    options=[{'label':'Particulate Matter','value':'PM'},
                                                                            {"label":'Ozone','value':'OZ'},
                                                                            {"label":'Other Gasses','value':'Gas'}])
                                                    ])
                                        ])
                                    ]),
                                html.Div(className='eight columns div-for-charts bg-grey',id="showGraphs",
                                            children=[
                                                html.Div(id='Choropleth-graph',
                                                    children=[
                                                    dcc.Graph('state-graph',config={'displayModeBar': False}),
                                                    dcc.Slider(id='year_slider',min=min(years),max=max(years),value=1997,
                                                                marks={str(y) : {'label' : str(y), 'style':{"transform": "rotate(45deg)",'font-size':'14px'}} for y in range(1920, 2018)})]),

                                                dcc.Graph(id = 'Pollutants-by-county',config={'displayModeBar': False}, style={'height':300})
                                                ]),
                                ])
                        ])


##Generating dropdowns
def add_AQI_class(sdf):
    state_class = []
    for index, row in sdf.iterrows():
        for aqindex,aqirow in aqi_class.iterrows():
            if row['AQI'] >= aqirow['AQI'] and row['AQI'] < aqirow['AQI.1']:
                state_class.append(aqirow['AQI Classification'])
    return pd.Series(state_class,dtype='object')

#Generate dropdwon for counties
@app.callback(
Output('county_select','options'),
[Input('state','value')])
def update_county(state):
    if state != 'USA':
        county = cdf[cdf['state_abv']==state]['county_name'].unique()
        counties = [{'label': i, 'value': i} for i in county]
    return counties

#hide Choro graph when first loading
@app.callback(Output('Choropleth-graph', 'style'),
[Input('state', 'value')])
def hide_Choropleth(state):
    if state:
        return {'display':'block'}
    return {'display':'none'}

#hide county line plot
@app.callback(Output('Pollutants-by-county', 'style'),
[Input('county_select','value'),
Input('pollutant_select','value'),
Input('state','value')])
def hide_pollutants(county,pollutant,state):
    if county and pollutant and state:
        return {'display':'block'}
    return {'display':'none'}

#hide dropdowns if USA choro selected
@app.callback(Output('div-for-pollutant-state','style'),
[Input('state','value')])
def hide_dropdowns(state):
    if state == 'USA':
        return {'display':'none'}
    else:
        return {'display':'block'}

#hide dropdowns if USA choro selected
# @app.callback(Output('county_select','style'),
# [Input('state','value')])
# def hide_dropdowns(state):
#     if state == 'USA':
#         return {'display':'none','width': '140px'}
#     else:
#         return {'display':'block','width': '140px'}
# ----- Generating County Plots -------- #

#county line plot
@app.callback(
Output('Pollutants-by-county','figure'),
[Input('state','value'),
Input('county_select','value'),
Input('pollutant_select','value')])
def show_county_breakdown(state,county,pollutant):
    countydf = edf[(edf['state_abv']==state)&(edf['county_name']==county)]
    countydf = countydf.groupby(['year','parameter_name'],as_index=False)['AQI'].mean()
    if pollutant == 'PM':
        df = countydf[(countydf['parameter_name']=='PM2.5')|(countydf['parameter_name']=='PM10')]
    elif pollutant == 'OZ':
        df = countydf[(countydf['parameter_name']=='O3 1-hr')|(countydf['parameter_name']=='O3 8-hr')]
    elif pollutant == 'Gas':
        df = countydf[(countydf['parameter_name']=='CO')|(countydf['parameter_name']=='SO2')|(countydf['parameter_name']=='NO2')]
    fig = px.scatter(df,x='year',y='AQI',template='plotly_dark',color='parameter_name', trendline='lowess',
                    title=("%s County Pollutant Air Quality"%(county)))

    return fig

#state graph Choropleth
@app.callback(
    Output('state-graph', 'figure'),
    [Input('state', 'value'),
    Input('year_slider','value')])
def show_state_year(state,year):
    # if state == 'USA':
    #     usadf = cdf[cdf['year']==year]
    #     fig = go.Figure(go.Choroplethmapbox(geojson=counties, locations=usadf.fips, z=usadf.AQI,
    #                                 colorscale="Oranges",
    #                                 hovertext=usadf['county_name'],
    #                                 hoverlabel=dict(namelength=0),
    #                                 hovertemplate='County: %{hovertext}<br>AQI: %{z}',
    #                                 hoverinfo='none',name='AQI',showlegend=True,
    #                                 marker_opacity=0.5, marker_line_width=0,
    #                                 colorbar = dict(
    #                                     title = 'AQI',
    #                                     tickvals = [0,10,20,30,40,50,60],
    #                                     tickfont = dict(
    #                                         color='white'
    #                                     )
    #                                     )
    #                            ))
    #     fig.update_geos(fitbounds="locations", visible=False)
    #     fig.update_layout(mapbox_style="carto-darkmatter", mapbox_zoom=3, mapbox_center = {"lat": 37.0902, "lon": -95.7129})
    #     fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    #
    # else:
    df = cdf[(cdf['state_abv']==state)& (cdf['year']==year)]
    df = df.groupby(['year','fips','county_name'],as_index=False)['AQI'].mean()
    df['classification'] = add_AQI_class(df)
    fig = px.choropleth(df,geojson=counties, locations='fips', color='AQI',range_color=[0,60],
                    color_continuous_scale="Oranges",
                    scope="usa",title=("%s Air Quality Index by County: %d"%(state,year)),
                    template="plotly_dark",
                    hover_data=['classification'],
                    hover_name='county_name')
    fig.update_geos(fitbounds="locations", visible=False,showsubunits=True, subunitcolor="White")
    fig.update_layout(margin={"r":10,"t":30,"l":10,"b":10})
    return fig



if __name__ == '__main__':
    app.run_server(debug=True)
