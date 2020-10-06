import os
import sys
sys.path.insert(0, os.path.realpath(os.path.dirname(__file__)))
os.chdir(os.path.realpath(os.path.dirname(__file__)))

import dash
from dash.dependencies import Output, Event, Input
import dash_core_components as dcc
import dash_html_components as html
import plotly
import plotly.graph_objs as go
import sqlite3
import pandas as pd

from collections import Counter
import string
import regex as re
#from cache import cache
#from config import stop_words
import time
import pickle
conn = sqlite3.connect('test.db', check_same_thread=False)
punctuation = [str(i) for i in string.punctuation]
# Size of the map
'''sentiment_colors = {-1:"#EE6055",
                    -0.5:"#FDE74C",
                     0:"#FFE6AC",
                     0.5:"#D0F2DF",
                     1:"#9CEC5B",}
'''
app_colors = {
    'background': '#0C0F0A',
    'text': '#000000',
    'sentiment-plot':'#41EAD4',
    'volume-bar':'#003366',
    'someothercolor':'#FF206E',
}
POS_NEG_NEUT = 0
MAX_DF_LENGTH = 100
app = dash.Dash(__name__)

app.layout = html.Div(
    [   html.Div(className='container-fluid', children=[html.H2('Live Twitter Sentiment', style={'color':"#CECECE"}),
                                                        html.H5('Search:', style={'color':app_colors['text']}),
                                                  dcc.Input(id='sentiment_term', value='usa', type='text', style={'color':app_colors['someothercolor']}),
                                                  ],
                 style={'width':'98%','margin-left':10,'margin-right':10,'max-width':50000}),
        html.Div(className='row',children=[html.Div(dcc.Graph(id='live-graph', animate=False), className='col s12 m6 l6'),
                                           html.Div(dcc.Graph(id='line-graph', animate=False), className='col s12 m6 16')]),
        html.Div(className='row', children=[html.Div(id="recent-tweets-table", className='col s12 m6 l6')]),
        dcc.Interval(
           id='graph-update',
            interval=20*1000,
        ),
        dcc.Interval(
            id='line-graph-update',
            interval=1*1000
        ),
        dcc.Interval(
            id='recent-table-update',
            interval=2*1000),
    ],style={'margin-top':'-30px', 'height':'2000px',},
)
def df_resample_sizes(df, maxlen=MAX_DF_LENGTH):
    try:
        df_len = len(df)
        resample_amt = 100
        vol_df = df.copy()
        vol_df['volume'] = 1

        ms_span = (df.index[-1] - df.index[0]).seconds * 1000
        rs = int(ms_span / maxlen)

        df = df.resample('{}ms'.format(int(rs))).mean()
        df.dropna(inplace=True)

        vol_df = vol_df.resample('{}ms'.format(int(rs))).sum()
        vol_df.dropna(inplace=True)

        df = df.join(vol_df['volume'])

        return df
    except Exception as e:
        with open('errors.txt','a') as f:
            f.write(str(e))
            f.write('\n')

@app.callback(Output('live-graph', 'figure'),
              events=[Event('graph-update', 'interval')])

def update_geo_scatter():
    try:
        c = conn.cursor()
        df = pd.read_sql("SELECT * FROM position", conn)
        #scl=[[0,"rgb(255,0,0)"],[1,"rgb(0,128,0)"]]
        #print(df['longitude'])
        data=[dict(
            type='scattergeo',
            lon=df['longitude'],
            lat=df['latitude'],
            text=df['polarity'],
            mode='markers',
            marker=dict(size=3,
                        color=df['pol']
                        )
            )]
        
        layout = dict(
            title = 'Live Tweets on Globe<br>(Click and drag to rotate)',
            showlegend = False,
            autosize=False,
            height=700,
            width=700,
            geo = dict(
                showland = True,
                showlakes = True,
                showcountries = False,
                showocean = True,
                countrywidth = 0.5,
                landcolor = 'rgb(31,31,31)',
                lakecolor = 'rgb(102,102,102)',
                oceancolor = 'rgb(41,41,41)',
                projection = dict(
                    type = 'orthographic',
                    rotation = dict(
                        lon = -100,
                        lat = 40,
                        roll = 0
                    )            
                ),
                lonaxis = dict( 
                    showgrid = False
                ),
                lataxis = dict( 
                    showgrid = False
                )
            )
        )
            
        return dict( data=data, layout=layout )
    except Exception as e:
        print(str(e))
@app.callback(Output('line-graph', 'figure'),
              [Input(component_id='sentiment_term', component_property='value')],
              events=[Event('line-graph-update', 'interval')])
def update_graph_scatter(sentiment_term):
    try:
        if sentiment_term:
            df = pd.read_sql("SELECT sentiment.* FROM sentiment_fts fts LEFT JOIN sentiment ON fts.rowid = sentiment.id WHERE fts.sentiment_fts MATCH ? ORDER BY fts.rowid DESC LIMIT 1000", conn, params=(sentiment_term+'*',))
        else:
            df = pd.read_sql("SELECT * FROM sentiment ORDER BY id DESC, unix DESC LIMIT 1000", conn)
        df.sort_values('unix', inplace=True)
        df['date'] = pd.to_datetime(df['unix'], unit='ms')
        df.set_index('date', inplace=True)
        init_length = len(df)
        df['sentiment_smoothed'] = df['sentiment'].rolling(int(len(df)/5)).mean()
        df = df_resample_sizes(df)
        X = df.index
        Y = df.sentiment_smoothed.values
        Y2 = df.volume.values
        data = plotly.graph_objs.Scatter(
                x=X,
                y=Y,
                name='Sentiment',
                mode= 'lines',
                yaxis='y2',
                line = dict(color = (app_colors['sentiment-plot']),
                            width = 4,)
                )

        data2 = plotly.graph_objs.Bar(
                x=X,
                y=Y2,
                name='Volume',
                marker=dict(color=app_colors['volume-bar']),
                )

        return {'data': [data,data2],'layout' : go.Layout(xaxis=dict(range=[min(X),max(X)]),
                                                          yaxis=dict(range=[min(Y2),max(Y2)], title='Volume', side='right'),
                                                          yaxis2=dict(range=[min(Y),max(Y)], side='left', overlaying='y',title='sentiment'),
                                                          title='Live sentiment for: "{}"'.format(sentiment_term),
                                                          font={'color':app_colors['text']},
                                                          #plot_bgcolor = app_colors['background'],
                                                          #paper_bgcolor = app_colors['background'],
                                                          showlegend=False)}

    except Exception as e:
        with open('errors.txt','a') as f:
            f.write(str(e))
            f.write('\n')

def quick_color(s):
    # except return bg as app_colors['background']
    if s >= POS_NEG_NEUT:
        # positive
        return "#7CFC00"
    elif s <= -POS_NEG_NEUT:
        # negative:
        return "#FFA07A"

    else:
        return app_colors['background']
def generate_table(df, max_rows=10):
    return html.Table(className="responsive-table",
                      children=[
                          html.Thead(
                              html.Tr(
                                  children=[
                                      html.Th(col.title()) for col in df.columns.values],
                                  style={'color':'#000000'}
                                  )
                              ),
                          html.Tbody(
                              [
                                  
                              html.Tr(
                                  children=[
                                      html.Td(data) for data in d
                                      ], style={'color':'#000000',
                                                'background-color':quick_color(d[2])}
                                  )
                               for d in df.values.tolist()])
                          ]
    )


def pos_neg_neutral(col):
    if col >= POS_NEG_NEUT:
        # positive
        return 1
    elif col <= -POS_NEG_NEUT:
        # negative:
        return -1

    else:
        return 0
    
            
@app.callback(Output('recent-tweets-table', 'children'),
              [Input(component_id='sentiment_term', component_property='value')],
              events=[Event('recent-table-update', 'interval')])        
def update_recent_tweets(sentiment_term):
    if sentiment_term:
        df = pd.read_sql("SELECT sentiment.* FROM sentiment_fts fts LEFT JOIN sentiment ON fts.rowid = sentiment.id WHERE fts.sentiment_fts MATCH ? ORDER BY fts.rowid DESC LIMIT 10", conn, params=(sentiment_term+'*',))
    else:
        df = pd.read_sql("SELECT * FROM sentiment ORDER BY id DESC, unix DESC LIMIT 10", conn)

    df['date'] = pd.to_datetime(df['unix'], unit='ms')

    df = df.drop(['unix','id'], axis=1)
    df = df[['date','tweet','sentiment']]

    return generate_table(df, max_rows=10)


external_css = ["https://cdnjs.cloudflare.com/ajax/libs/materialize/0.100.2/css/materialize.min.css"]
for css in external_css:
    app.css.append_css({"external_url": css})


external_js = ['https://cdnjs.cloudflare.com/ajax/libs/materialize/0.100.2/js/materialize.min.js',
               'https://pythonprogramming.net/static/socialsentiment/googleanalytics.js']
for js in external_js:
    app.scripts.append_script({'external_url': js})
if __name__=='__main__':
    app.run_server(debug=True)
#plotly.offline.plot( fig, validate=False, filename='d3-globe' )    
