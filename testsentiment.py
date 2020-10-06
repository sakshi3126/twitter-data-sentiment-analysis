import os
import sys
sys.path.insert(0, os.path.realpath(os.path.dirname(__file__)))
os.chdir(os.path.realpath(os.path.dirname(__file__)))

from tweepy import Stream
from tweepy import OAuthHandler
from tweepy.streaming import StreamListener
import json
import sqlite3
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from unidecode import unidecode
import time
from threading import Lock, Timer
import pandas as pd
#from config import stop_words
import regex as re
from collections import Counter
import string
import pickle
import itertools
from textblob import TextBlob
analyzer=SentimentIntensityAnalyzer()
ckey="pnEJ0K4t9MD0mjAPzYEV0RXuC"
csecret="qfcQRjF9tpYpmqOzB1Xd211UM0slaLgodSlTNDjUY7JZr8x9V0"
atoken="766837928957911040-RBHFyZoWHEnkMU85O59g91meJlMBS3R"
asecret="IeyyzTYwkkJQ7dP5xYjrtkIDtbaKgeJAW3k2zPtImOB00"
conn = sqlite3.connect('test.db', isolation_level=None, check_same_thread=False)
c = conn.cursor()
def create_table():
    try:
        c.execute("PRAGMA journal_mode=wal")
        c.execute("PRAGMA wal_checkpoint=TRUNCATE")
        c.execute("CREATE TABLE IF NOT EXISTS position(longitude REAL, latitude REAL, polarity TEXT, pol REAL)")
        c.execute("CREATE TABLE IF NOT EXISTS sentiment(id INTEGER PRIMARY KEY AUTOINCREMENT,unix REAL, tweet TEXT, sentiment REAL)")
        #c.execute("CREATE TABLE IF NOT EXISTS misc(key TEXT PRIMARY KEY, value TEXT)")
        c.execute("CREATE VIRTUAL TABLE sentiment_fts USING fts5(tweet, content=sentiment, content_rowid=id, prefix=1, prefix=2, prefix=3)")
        c.execute("""
            CREATE TRIGGER sentiment_insert AFTER INSERT ON sentiment BEGIN
                INSERT INTO sentiment_fts(rowid, tweet) VALUES (new.id, new.tweet);
            END
        """)
        #conn.commit()
    except Exception as e:
        print(str(e))
create_table()

lock=Lock()
class listener(StreamListener):
    data=[]
    data1=[]
    lock=None
    def __init__(self,lock):
        self.lock=lock
        self.save_in_database()
        super().__init__()
    def save_in_database(self):
        Timer(1,self.save_in_database).start()
        with self.lock:
            if len(self.data):
                c.execute('BEGIN TRANSACTION')
                try:
                    c.executemany("INSERT INTO sentiment (unix, tweet, sentiment) VALUES (?, ?, ?)", self.data)
                except:
                    pass
                c.execute('COMMIT')
            if len(self.data1):
                c.execute('BEGIN TRANSACTION')
                try:
                    c.executemany("INSERT INTO position (longitude, latitude, polarity, pol) VALUES (?, ?, ?, ?)", self.data1)
                except:
                    pass
                c.execute('COMMIT')

                self.data = []
                self.data1=[]
                
    def on_status(self, tweet):
        try:
            data=tweet.text
            time_ms=tweet.timestamp_ms
            vs=analyzer.polarity_scores(data)
            sentiment=vs['compound']
            if sentiment!=0:
                with self.lock:
                    self.data.append((time_ms, data, sentiment))
            #c.execute("INSERT INTO sentiment(unix, tweet, polarity) VALUES(?,?,?)",(time_ms,data,sentiment))
                if tweet.coordinates is not None:
                    x=tweet.coordinates['coordinates'][0]
                    y=tweet.coordinates['coordinates'][1]
                    if sentiment<0:
                        color='rgb(255,0,0)'
                    elif sentiment>0:
                        color='rgb(0,128,0)'
                    with self.lock:
                        self.data1.append((x, y, sentiment, color))
                '''c.execute("INSERT INTO position (latitude, longitude, polarity) VALUES(?,?,?)",
                          (x, y, color))'''
                #conn.commit()
        except KeyError as e:
            print(str(e))
        return True
            
    def on_error(self, status):
        print(status)


while True:
    try:
        auth = OAuthHandler(ckey,csecret)
        auth.set_access_token(atoken,asecret)
        twitterStream=Stream(auth,listener(lock))
        twitterStream.filter(locations=[-180, -90, 180, 90])
    except Exception as e:
        print(str(e))
        time.sleep(5)
