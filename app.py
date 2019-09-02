# Imports the Google Cloud client library
import re
import tweepy
import redis
import json
import time
from multiprocessing import Process
from flask import Flask, Response, request, render_template
from werkzeug.datastructures import Headers
from flask_cors import CORS
from tweepy import OAuthHandler 
from google.cloud import language
from google.cloud.language import enums
from google.cloud.language import types
from google.api_core.exceptions import InvalidArgument

redis_host = "redisdb"
redis_port = 6379
redis_password = ""
r = redis.StrictRedis(host=redis_host, port=redis_port, password=redis_password, decode_responses=True)

class MyStreamListener(tweepy.StreamListener):
	
	def strToArray(self, s):
		return s.split(',')

	def __init__(self, hashtag, *args, **kwargs):
		super(self.__class__, self).__init__(*args, **kwargs)
		self.start_time = time.time()
		self.limit = 30
		self.client = language.LanguageServiceClient()	
		self.store = {}

		if hashtag != '':
			self.searchKey = hashtag
		else:
			self.searchKey = 'Toronto,FaceToFace'
		#self.searchKey = 'Toronto,FaceToFace'

		consumer_key = 'H9QuSJOBP5TIamIit3z45ucxw'
		consumer_secret = 'GrRp1blE8VGGLlvUsCeJaH95CA4ruunC1E7Qx5MuGYb4DL1mRq'
		access_token = '385537076-tZKbwCtw2Yh02JD62C3m1utclE3L2oS1h2Boyump'
		access_token_secret = 'qv5O4uX3S3dk4dE84JpdLheIkA7kCmV6CqZUAwyqTzIQ9'

		
		# attempt authentication 
		try: 
			auth = OAuthHandler(consumer_key, consumer_secret) 
			auth.set_access_token(access_token, access_token_secret) 
			api = tweepy.API(auth)

		except Exception as e:
			print("Error : " + str(e)) 

		#myStreamListener = MyStreamListener()
		self.myStream = tweepy.Stream(auth = api.auth, listener=self)
		self.myStream.filter(track=self.strToArray(self.searchKey))

	def change_filter(self, s):
		print(u"Changing filter to " + s)
		self.searchKey = s
		self.myStream.disconnect();
		try:
			self.myStream.filter(track=self.strToArray(self.searchKey))
		except Exception as e:
			print("Restart error :" + str(e))

	def on_status(self, status):
		#print(u"Called")

		try:
			if hasattr(status, 'retweeted_status') or status.retweeted == 'true':
				raise Exception("retweet")

			if status.id in self.store:
				print("duplicate tweet")
				raise Exception("duplicate tweet")
			
			self.store[status.id] = 1
			#print(status.retweeted)
			#print(str(status.id) + " - " + str(len(self.store)))
			#print(status.text)
			try:
				text = status.extended_tweet["full_text"]
			except AttributeError:
				text = status.text

			tweet = self.clean_tweet(text)
			#print("\nReceived Tweet :" + tweet)
			
			document = types.Document(content=tweet, type=enums.Document.Type.PLAIN_TEXT)
			
			sentiment = self.client.analyze_sentiment(document=document).document_sentiment
			tokens = self.client.analyze_syntax(document).tokens
			result = self.client.analyze_entity_sentiment(document=document)
			
			adj = ""
			senti = ""
			noun = ""
			words = {}
			
			for entity in result.entities:
				if entity.name != "RT":
					words[entity.name] = entity.sentiment.score

			for token in tokens:
				part_of_speech_tag = enums.PartOfSpeech.Tag(token.part_of_speech.tag)
				if part_of_speech_tag.name == 'ADJ':
					adj = token.text.content
					break

			if adj == "":
				for token in tokens:
					part_of_speech_tag = enums.PartOfSpeech.Tag(token.part_of_speech.tag)
					if part_of_speech_tag.name == 'VERB':
						adj = token.text.content
						break

			if sentiment.score > 0.25: 
				#print("\npositive {}".format(sentiment.score))
				senti = "POSITIVE"
				if len(words) > 0:
					noun = max(words, key=words.get)
			elif sentiment.score < -0.25: 
				senti = "NEGATIVE"
				if len(words) > 0:
					noun = min(words, key=words.get)
			else: 
				senti = "NEUTRAL"
				if len(words) > 0:
					noun = min(words, key=words.get)
			
			message = json.dumps({'sentiment': sentiment.score, 'adj': adj, 'noun': noun, 'tweet': tweet, 'hashtag': self.searchKey})
			#message = json.dumps({'sentiment': 0.5, 'adj': tweet.split(' ',1)[0], 'noun': tweet.split(' ',1)[0], 'tweet': tweet, 'hashtag': self.searchKey})
			r.publish("tweet", message)
			#print("\n Sent: " + tweet)

		except Exception as e:
			#print(u"error " + str(e))
			if str(e) != "retweet":
				print(u"error " + str(e))

		finally:
			if (time.time() - self.start_time) > self.limit:
				print("time's up")
				message = json.dumps({'end': 1})
				r.publish("tweet", message)
				return False

	def clean_tweet(self, tweet): 
		''' 
		Utility function to clean tweet text by removing links, special characters 
		using simple regex statements. 
		'''
		return ' '.join(re.sub("(@[A-Za-z0-9]+)|([^0-9A-Za-z \t]) |(\w+:\/\/\S+)", " ", tweet).split())

	def on_error(self, status_code):
		if status_code == 420:
			print("420 error")
			return False


	
def event_stream():
    pubsub = r.pubsub()
    pubsub.subscribe('tweet')
    print("Subscribed")
    for message in pubsub.listen():
    	yield "data: %s\n\n" % message['data']



app = Flask(__name__)
CORS(app)

streamHead = Headers()
streamHead.add('Content-Type', 'text/event-stream')
streamHead.add('Cache-Control', 'no-cache')
streamHead.add('X-Accel-Buffering', 'no')

@app.route('/')
def hello_world():
    return render_template('tweets.htm')
    #return 'Hello, World!'

@app.route("/stream")
def stream():
	return Response(event_stream(), mimetype="text/event-stream", headers=streamHead)


@app.route("/start", methods=['POST'])
def startstream():
	data = request.get_json()
	if data['hashtag'] != '':
		print(data['hashtag'])
		p1 = Process(target=MyStreamListener, args=(data['hashtag'],))
		#p1 = Process(target=MyStreamListener)
		p1.start()
	return "1"


if __name__ == "__main__": 
	# calling main function 
	#main() 
	#download_thread = threading.Thread(target=MyStreamListener())
	#download_thread.start()
	#app.debug = True
	app.run(debug=True, host='0.0.0.0')
	#print("is this callsed?")
	#MyStreamListener()