# SentiMuse_TweetAnalyzer

## SentiMuse Project

### Docker Container with Python + Redis + Tweepy + Google Natural Language Processing

Tweet Analyzer Component written in Python.  
Tweets are streamed by Tweepy and Analyzed for Sentiments, Entities and Syntax using Google Natural Language Processing.  
Result is then published onto Redis Stream to be read by clients connected to :5000/stream via EventSource.  

The next component of this SentiMuse Project is a web app to read from this stream and auto generate music reflecting the sentiments realtime.  

