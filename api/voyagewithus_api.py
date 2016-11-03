# -*- coding: utf-8 -*-

@author: Sonia
"""

import urllib2
from google.appengine.ext import ndb
from google.appengine.api import mail
import webapp2
import json
from datetime import datetime,timedelta
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.api.images import get_serving_url
#TODO - wait until google app engine decides to support locale settings
#from functools import cmp_to_key
#import locale
#locale.setlocale(locale.LC_ALL, 'en_US.UTF-8') # vary depending on your lang/locale
#assert sorted((u'Ab', u'ad', u'aa'),key=cmp_to_key(locale.strcoll)) == [u'aa', u'Ab', u'ad']
APP_ID = "e8be5c40"
API_KEY = "3960dd544fab6cbe5204363ddeeca1e5"

statusMessage={
    0:'OK',
    1:'trip Created',
    2:'trip Already Exists',
    3:'you are not allowed to perform this operation',
    99:'Unknown error'
}

# model classes
def trip_key(trip_name):
    """Constructs a Datastore key for a Trip entity"""
    return ndb.Key('Trip', trip_name)

class Trip(ndb.Model):
    """Models an individual trip entry."""
    owner = ndb.StringProperty(required=True)
    name = ndb.StringProperty(required=True)
    accessLevel = ndb.StringProperty(required=True)
    coverUrl = ndb.StringProperty(required=True)
    subscribers=ndb.StringProperty(repeated=True)
    invitees=ndb.StringProperty(repeated=True)
    travelers = ndb.StringProperty(repeated=True)
    startDate = ndb.DateTimeProperty(required=True)
    endDate = ndb.DateTimeProperty(required=True)
    lat = ndb.FloatProperty(required=True)
    long = ndb.FloatProperty(required=True)
    location = ndb.StringProperty(required=True)

class TripArtifact(ndb.Model):
    parentTrip = ndb.StructuredProperty(Trip)
    name = ndb.StringProperty(required=True)
    type = ndb.StringProperty(required=True)
    checkIn = ndb.DateTimeProperty(required=True)
    checkOut = ndb.DateTimeProperty(required=True)
    address = ndb.StringProperty(required=True)
    lat = ndb.FloatProperty
    long = ndb.FloatProperty
    company = ndb.StringProperty(required=True)
    reservationNo = ndb.StringProperty(required=True)
    fromLocation = ndb.StringProperty(required=True)
    toLocation = ndb.StringProperty(required=True)

class TripPhoto(ndb.Model):
    """Models an individual Photo entry."""
    parenttrip=ndb.StructuredProperty(Trip)
    name = ndb.StringProperty(required=True)
    url=ndb.StringProperty(required=True)

def prefs_key(user_name):
    """Constructs a Datastore key for a User prefs entity"""
    return ndb.Key('UserPrefs', user_name)
    
class UserPrefs(ndb.Model):
    userId=ndb.StringProperty()
    updateRate=ndb.StringProperty()
    lastEmail=ndb.DateTimeProperty(auto_now=True)

def user_key(user_id):
    return ndb.Key('User', user_id)

class User(ndb.Model):
    id = ndb.StringProperty(required=True)
    name = ndb.StringProperty(required=True)
    country = ndb.StringProperty(required=False)

def sentiment_key(id):
    return ndb.Key('Sentiment', id)

class Sentiment(ndb.Model):
    id = ndb.StringProperty(required=True)
    user = ndb.StringProperty(required=True)
    text = ndb.StringProperty(required=False)
    poi = ndb.StringProperty(required=True)
    rating = ndb.FloatProperty(required=True)

def poi_key(poi_name):
    return ndb.Key('Poi', poi_name)

class Poi(ndb.Model):
    name = ndb.StringProperty(required=True)
    lat = ndb.FloatProperty(required=True)
    long = ndb.FloatProperty(required=True)
    location = ndb.StringProperty(required=True)
    goodForGroups = ndb.StringProperty(required=True)
    open = ndb.StringProperty(required=True)
    close = ndb.StringProperty(required=True)

class MainPage(webapp2.RequestHandler):
    def get(self):
        self.response.write('This is a trip managing API')

#api endpoints
class AllTrips(webapp2.RequestHandler):
    # TODO - account for access control
    def get(self):
        response = {"trips": []}
        allTrips = Trip.query().order(Trip.startDate).fetch()
        for trip in allTrips:
                response["trips"].append(
                    {'tripName': trip.name, 'coverUrl': trip.coverUrl, 'lat': trip.lat, 'lon': trip.long,
                     'location': trip.location, 'startDate': trip.startDate.strftime('%d/%m/%Y'),
                     'endDate': trip.endDate.strftime('%d/%m/%Y'), 'accessLevel': trip.accessLevel})
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(response))
    def post(self):
        status=statusMessage[0]
        params=json.loads(urllib2.unquote(self.request.body).decode('ISO-8859-1'))
        try:
            trip=Trip(key = trip_key(params['name']))
            trip.name=params['name']
            trip.owner=params['user']
            trip.coverUrl = params['coverUrl']
            try:
                trip.invitees = params['invitees']
            except Exception,e:
                error = e
            trip.startDate = datetime.strptime(params['startDate'], '%m/%d/%Y')
            trip.endDate = datetime.strptime(params['endDate'], '%m/%d/%Y')
            trip.accessLevel = params['accessLevel']
            trip.lat = float(params['lon'])
            trip.long = float(params['lat'])
            trip.location = params['location']
            trip.travelers.append(trip.owner)
            if Trip.get_by_id(params['name'])==None:
                trip.put()
                send_mail(params['user'],params['invitees'],"VoyageWithUS Notification","You are invited to %s. Follow this link to RSVP"%(params['name']))
                status=statusMessage[0]
            else:
                status=statusMessage[2]
        except Exception,e:
            print e
        self.response.headers['Content-Type'] = 'application/json'
        response={"status":str(status)}
        self.response.write(json.dumps(response))

class Trips(webapp2.RequestHandler):
    def get(self, tripId):
        response = {"trip": []}
        trip = Trip.get_by_id(tripId)
        response["trip"].append({'name': trip.name, 'startDate': trip.startDate.strftime('%d/%m/%Y'),
                                'endDate': trip.endDate.strftime('%d/%m/%Y'), 'lat': trip.lat, 'lon': trip.long,
                                'location': trip.location, 'travelers': trip.travelers, 'invitees': trip.invitees,
                                'owner': trip.owner, 'url': trip.coverUrl})
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(response))
    def put(self, tripId):
        status=statusMessage[0]
        params=json.loads(urllib2.unquote(self.request.body).decode('ISO-8859-1'))
        try:
            trip = Trip.get_by_id(tripId)
            if (trip != None) and ((trip.owner==params['user'])or(params['user'] in trip.travelers)):
                if (params['startDate'] is not None) and (params['startDate'] is not ""):
                    trip.startDate = datetime.strptime(params['startDate'], '%m/%d/%Y')
                if (params['endDate'] is not None) and (params['endDate'] is not ""):
                    trip.endDate = datetime.strptime(params['endDate'], '%m/%d/%Y')
                if (params['accessLevel'] is not None) and (params['accessLevel'] is not ""):
                    trip.accessLevel = params['accessLevel']
                if (params['lat'] is not None) and (params['lat'] is not ""):
                    trip.lat = float(params['lon'])
                if (params['lon'] is not None) and (params['lon'] is not ""):
                    trip.long = float(params['lat'])
                if (params['location'] is not None) and (params['location'] is not ""):
                    trip.location = params['location']
                send_mail(trip.owner,trip.invitees+trip.subscribers+trip.travelers,"VoyageWithUS Notification","Trip %s has been updated"%(trip.name))
                trip.put()
                status=statusMessage[0]
            else:
                status=statusMessage[3]
        except Exception,e:
            error=e
        self.response.headers['Content-Type'] = 'application/json'
        response={"status":str(status)}
        self.response.write(json.dumps(response))
    def delete(self, tripId):
        response={'status':[]}
        try:
            trip = Trip.get_by_id(tripId)
            if (trip != None):
                trip.key.delete()
                send_mail(trip.owner,trip.invitees+trip.subscribers+trip.travelers,"Trip %s has been cancelled by its owner"%(trip.name))
                status=statusMessage[0]
            else:
                status=statusMessage[3]
        except Exception,e:
            error=e
        response["status"].append("%s Deleted"%(trip.name))
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(response))

class UserTrips(webapp2.RequestHandler):
    def get(self, userId):
        user = userId
        response={"owned":[],"subscribed":[],"invited":[],"joined":[]}
        ownedtrips=Trip.query(Trip.owner==user).order(Trip.startDate).fetch()
        for trip in ownedtrips:
            response['owned'].append({'tripName':trip.name,'tripCover':trip.coverUrl,'location':trip.location,'startDate':trip.startDate.strftime('%d/%m/%Y'),'endDate':trip.endDate.strftime('%d/%m/%Y')})
        subscribedtrips=Trip.query(Trip.subscribers.IN([user])).fetch()
        for trip in subscribedtrips:
            response['subscribed'].append({'tripName':trip.name,'tripCover':trip.coverUrl,'location':trip.location,'startDate':trip.startDate.strftime('%d/%m/%Y'),'endDate':trip.endDate.strftime('%d/%m/%Y')})
        invitedtrips=Trip.query(Trip.invitees.IN([user])).fetch()
        for trip in invitedtrips:
            response['invited'].append({'tripName':trip.name,'tripCover':trip.coverUrl,'location':trip.location,'startDate':trip.startDate.strftime('%d/%m/%Y'),'endDate':trip.endDate.strftime('%d/%m/%Y')})
        joinedtrips=Trip.query(Trip.travelers.IN([user])).fetch()
        for trip in joinedtrips:
            response['joined'].append({'tripName':trip.name,'tripCover':trip.coverUrl,'location':trip.location,'startDate':trip.startDate.strftime('%d/%m/%Y'),'endDate':trip.endDate.strftime('%d/%m/%Y')})
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(response))

class PastTrips(webapp2.RequestHandler):
    def get(self, userId):
        user = userId
        response={"trips":[]}
        allTrips=Trip.query().order(Trip.startDate).fetch()
        for trip in allTrips:
            if (trip.startDate < datetime.now()) and (trip.endDate < datetime.now()):
                if (trip.owner==user) or (user in trip.travelers):
                    response["trips"].append({'tripName':trip.name,'coverUrl':trip.coverUrl,'lat':trip.lat,'lon':trip.long, 'location':trip.location, 'startDate':trip.startDate.strftime('%d/%m/%Y'),'endDate':trip.endDate.strftime('%d/%m/%Y'),'accessLevel':trip.accessLevel})
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(response))

class CurrentTrips(webapp2.RequestHandler):
    def get(self, userId):
        user = userId
        response={"trips":[]}
        allTrips=Trip.query().order(Trip.startDate).fetch()
        for trip in allTrips:
            if (trip.startDate >= datetime.now()) or (trip.endDate >= datetime.now()):
                if (trip.owner==user) or (user in trip.travelers):
                    response["trips"].append({'tripName':trip.name,'coverUrl':trip.coverUrl,'lat':trip.lat,'lon':trip.long, 'location':trip.location, 'startDate':trip.startDate.strftime('%d/%m/%Y'),'endDate':trip.endDate.strftime('%d/%m/%Y'),'accessLevel':trip.accessLevel})
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(response))

class Artifacts(webapp2.RequestHandler):
    def get(self, artifactId, tripId):
        response = {"trip": []}
        trip = Trip.get_by_id(tripId)
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(response))
    def post(self):
        status=statusMessage[0]
        params=json.loads(urllib2.unquote(self.request.body).decode('ISO-8859-1'))
        #params=json.loads(unicode(opener.open(self.request.body),"ISO-8859-1"))
        try:
            parentTrip=Trip.get_by_id(params['tripId'])
            artifact = TripArtifact(parent=parentTrip.key)
            artifact.type = params['type']
            artifact.company = params['company']
            artifact.address = params['address']
            artifact.fromLocation = params['fromLocation']
            artifact.toLocation = params['toLocation']
            artifact.reservationNo = params['reservationNo']
            artifact.checkIn = datetime.strptime(params['startDate'], '%m/%d/%Y')
            artifact.checkOut = datetime.strptime(params['endDate'], '%m/%d/%Y')
            artifact.parentTrip = parentTrip
            #TODO - hash
            artifact.name=artifact.type+artifact.company+params['startDate']+params['endDate']+params['tripId']+params['reservationNo']
            artifact.put()
        except Exception,e:
            error=e
        send_mail(parentTrip.owner,parentTrip.travelers,"VoyageWithUS Notification","New artifact added to trip  %s"%(params['tripId']))
        self.response.headers['Content-Type'] = 'application/json'
        response={"status":str(status)}
        self.response.write(json.dumps(response))
    def put(self, artifactId, tripId):
        status = statusMessage[0]
        try:
            parentTrip = Trip.get_by_id(tripId)
            artifactName = artifactId
            artifactQuery = TripArtifact.query(ancestor=trip_key(parentTrip.name))
            allArtifacts = artifactQuery.fetch()
            for artifact in allArtifacts:
                if artifact.name == artifactName:
                    artifact.company = params['company']
                    artifact.address = params['address']
                    artifact.fromLocation = params['fromLocation']
                    artifact.toLocation = params['toLocation']
                    artifact.reservationNo = params['reservationNo']
                    artifact.checkIn = datetime.strptime(params['startDate'], '%m/%d/%Y')
                    artifact.checkOut = datetime.strptime(params['endDate'], '%m/%d/%Y')
                    artifact.parentTrip = parentTrip
                    # TODO - hash
                    artifact.put()
        except Exception, e:
            error = e
        send_mail(parentTrip.owner, parentTrip.travelers, "VoyageWithUS Notification",
                  "Artifact updated in trip  %s" % (params['tripId']))
        self.response.headers['Content-Type'] = 'application/json'
        response = {"status": str(status)}
        self.response.write(json.dumps(response))
    def delete(self, artifactId, tripId):
        response = {'status': []}
        try:
            parentTrip = Trip.get_by_id(tripId)
            artifactName = artifactId
            artifactQuery = TripArtifact.query(ancestor=trip_key(parentTrip.name))
            allArtifacts = artifactQuery.fetch()
            for artifact in allArtifacts:
                if artifact.name == artifactName:
                    artifact.key.delete()
        except Exception, e:
            error = e
        response["status"].append("%s Deleted" % (artifactName))
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(response))

class TripArtifacts(webapp2.RequestHandler):
    def get(self, tripId):
        response = {"artifacts": []}
        status = statusMessage[0]
        parentTrip = Trip.get_by_id(tripId)
        artifactQuery = TripArtifact.query(ancestor=trip_key(parentTrip.name)).order(TripArtifact.checkIn)
        allArtifacts = artifactQuery.fetch()
        for artifact in allArtifacts:
            response["artifacts"].append(
                {'name': artifact.name, 'company': artifact.company, 'address': artifact.address,
                 'fromLocation': artifact.fromLocation, 'toLocation': artifact.toLocation,
                 'confirmation': artifact.reservationNo, 'startDate': artifact.checkIn.strftime('%d/%m/%Y'),
                 'endDate': artifact.checkOut.strftime('%d/%m/%Y'), 'type': artifact.type})
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(response))

class CreateUsers(webapp2.RequestHandler):
    def get(self):
        response = {"users": []}
        allUsers = User.query().order(User.name).fetch()
        for user in allUsers:
            response["users"].append({'userName': user.name, 'ID': user.id, 'location': user.country})
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(response))
    def post(self):
        status = statusMessage[0]
        params = json.loads(urllib2.unquote(self.request.body).decode('ISO-8859-1'))
        # params=json.loads(unicode(opener.open(self.request.body),"ISO-8859-1"))
        try:
            user = User(key = user_key(params['id']))
            user.name = params['name']
            user.country = params['country']
            user.id = params['id']
            user.put()
        except Exception, e:
            error = e
        self.response.headers['Content-Type'] = 'application/json'
        response = {"status": str(status)}
        self.response.write(json.dumps(response))

class Users(webapp2.RequestHandler):
    def get(self, userId):
        response = {"user": []}
        user = User.get_by_id(userId)
        response["user"].append({'name': user.name, 'id': user.id,
                                 'location': trip.endDate.strftime('%d/%m/%Y')})
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(response))
    def put(self, userId):
        status = statusMessage[0]
        params = json.loads(urllib2.unquote(self.request.body).decode('ISO-8859-1'))
        try:
            user = User.get_by_id(userId)
            if (user != None):
                if (params['name'] is not None) and (params['name'] is not ""):
                    user.name = params['name']
                if (params['location'] is not None) and (params['location'] is not ""):
                    user.country = params['country']
                user.put()
                status = statusMessage[0]
            else:
                status = statusMessage[3]
        except Exception, e:
            error = e
        self.response.headers['Content-Type'] = 'application/json'
        response = {"status": str(status)}
        self.response.write(json.dumps(response))
    def delete(self, userId):
        response = {'status': []}
        try:
            user = User.get_by_id(userId)
            if (user != None):
                user.key.delete()
                status = statusMessage[0]
            else:
                status = statusMessage[3]
        except Exception, e:
            error = e
        response["status"].append("%s Deleted" % (user.name))
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(response))

class Sentiments(webapp2.RequestHandler):
    def get(self):
        response = {"reviews": []}
        allReviews = Sentiment.query().order(Sentiment.id).fetch()
        for review in allReviews:
            response["reviews"].append({'id': review.id, 'user': review.user, 'poi': review.poi,
                                        'review':review.text, 'rating':review.rating})
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(response))
    def post(self):
        status = statusMessage[0]
        params = json.loads(urllib2.unquote(self.request.body).decode('ISO-8859-1'))
        try:
            sentiment = Sentiment(key=sentiment_key(params['id']))
            sentiment.id = params['id']
            sentiment.user = params['user']
            sentiment.poi = params['poi']
            sentiment.text = params['review']
            sentiment.rating = params['rating']
            sentiment.put()
        except Exception, e:
            error = e
        self.response.headers['Content-Type'] = 'application/json'
        response = {"status": str(status)}
        self.response.write(json.dumps(response))

class SentimentsPois(webapp2.RequestHandler):
    def get(self, poiId):
        response = {"reviews": []}
        allReviews = Sentiment.query().order(Sentiment.id).fetch()
        for review in allReviews:
            if review.poi == poiId:
                response["reviews"].append({'id': review.id, 'user': review.user, 'poi': review.poi,
                                        'review': review.text, 'rating': review.rating})
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(response))

class SentimentsUsers(webapp2.RequestHandler):
    def get(self, userId):
        response = {"reviews": []}
        allReviews = Sentiment.query().order(Sentiment.id).fetch()
        for review in allReviews:
            if review.user == userId:
                response["reviews"].append({'id': review.id, 'user': review.user, 'poi': review.poi,
                                        'review': review.text, 'rating': review.rating})
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(response))

class AllPois(webapp2.RequestHandler):
    def get(self):
        return None
    def post(self):
        return None

class Pois(webapp2.RequestHandler):
    def get(self):
        return None
    def put(self):
        return None
    def delete(self):
        return None

class RecommendTrip(webapp2.RequestHandler):
    def get(self, tripId):
        #TODO invoke lambda job and return results
        return None

class RecommendNearby(webapp2.RequestHandler):
    def get(self):
        #TODO invoke lambda job and return results
        return None

class ItineraryWalking(webapp2.RequestHandler):
    def get(self):
        # TODO invoke lambda job and return results
        return None

class ItineraryTrip(webapp2.RequestHandler):
    def get(self):
        # TODO invoke Expedia and return results
        return None


# helper functions for image upload
class UploadImage(webapp2.RequestHandler):
    def post(self):
        uploadUrl = blobstore.create_upload_url('/upload')
        self.response.headers['Content-Type'] = 'multipart/form-data'
        self.response.out.write(uploadUrl)

class BlobUpload(blobstore_handlers.BlobstoreUploadHandler):  
    def post(self):
        try:
            upload_files = self.get_uploads('photo')
            blob_info = upload_files[0]
            key = blob_info.key()
            servingUrl = get_serving_url(key)
            parenttrip=Trip.get_by_id(self.request.get('tripId'))
            photo = TripPhoto(parent=parenttrip.key)  
            photo.name=self.request.get('name')
            photo.owner = parentTrip.owner
            photo.comments=self.request.get('comments')
            photo.url=servingUrl
            photo.put()
            if parenttrip.coverUrl == '':
                parenttrip.coverUrl = servingUrl
                parenttrip.put()
            send_mail("",parenttrip.subscribers,"Connexus Update - New photo uploaded to trip %s"%(parenttrip.name),"Photo %s"%(servingUrl)) 
        except:
            servingUrl="error.html"
        self.redirect(self.request.referer)


#user actions management
class Subscribe(webapp2.RequestHandler):
    def post(self):
        params=json.loads(urllib2.unquote(self.request.body).decode('utf8'))
        user = params["user"]
        trip = params["tripId"]
        trip = Trip.get_by_id(params['tripId'])
        trip.subscribers.append(user)
        trip.put()
        send_mail("",[user],"Voyage With Us - You are now subscribed to %s"%(trip.name),"")
        email = user
        pref = UserPrefs(key = prefs_key(email))
        pref.userId=email
        pref.updateRate='1'
        pref.lastEmail=datetime.now()
        if UserPrefs.get_by_id(email)==None:
            pref.put()
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write('Susbscribed')
        
class Unsubscribe(webapp2.RequestHandler):
    def post(self):
        params=json.loads(urllib2.unquote(self.request.body).decode('utf8'))
        user = params["user"]
        trips = params['tripIds']
        for tripName in trips:
            trip = Trip.get_by_id(tripName)
            if (trip != None):
                trip.subscribers.remove(user)
                trip.put()
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write('Unsusbscribed')

class JoinTrip(webapp2.RequestHandler):
    def post(self):
        params=json.loads(urllib2.unquote(self.request.body).decode('utf8'))
        print params
        user = params["user"]
        trip = params["tripId"]
        trip = Trip.get_by_id(params['tripId'])
        trip.travelers.append(user)
        trip.invitees.remove(user)
        trip.put()
        send_mail("",[user],"Voyage With Us - You are now traveling to %s"%(trip.name),"")
        email = user
        pref = UserPrefs(key = prefs_key(email))
        pref.userId=email
        pref.updateRate='1'
        pref.lastEmail=datetime.now()
        if UserPrefs.get_by_id(email)==None:
            pref.put()
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write('Susbscribed')

class LeaveTrip(webapp2.RequestHandler):
    def post(self):
        params=json.loads(urllib2.unquote(self.request.body).decode('utf8'))
        user = params["user"]
        trips = params['tripIds']
        for tripName in trips:
            trip = Trip.get_by_id(tripName)
            if (trip != None):
                trip.invitees.remove(user)
                trip.put()
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write('Unsusbscribed')

class ShareTrip(webapp2.RequestHandler):
    #TODO - add access control
    def post(self):
        params=json.loads(urllib2.unquote(self.request.body).decode('utf8'))
        users = params["users"]
        owner = params["owner"]
        trip = params["tripId"]
        trip = Trip.get_by_id(params['tripId'])
        print params
        print users
        if (trip.owner==owner):
            for user in users:
                print user
                trip.invitees.append(user)
                trip.put()
                send_mail("",[user],"VoyageWithUS Notification","Voyage With Us - You have been invited to %s"%(trip.name))
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write('Susbscribed')

class ReportingPreferences(webapp2.RequestHandler):
    #TODO - figure out cool way of subscribing people to update
    def post(self):
        params=json.loads(urllib2.unquote(self.request.body).decode('utf8'))
        emailUpdateRate = params["updateRate"]
        userId = params["user"]
        if UserPrefs.get_by_id(userId)==None:
            user = UserPrefs(key = prefs_key(userId))
            user.userId=userId
            user.lastEmail=datetime.now()
        else:
            user = UserPrefs.get_by_id(userId)
        user.updateRate=emailUpdateRate
        user.put()
        response={"updateRateChanged":emailUpdateRate}
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(response))

def send_mail(user,subscribers,subject,message):
    try:
        for subscriber in subscribers:
            mail.send_mail("sonia.marginean@gmail.com", subscriber, subject, message)
    except:
        print "Something went wrong"

class FlightUpdate(webapp2.RequestHandler):
    #call into flightstats
    def get(self):
        response={}
        digest = ""
        artifacts=TripArtifact.query().order(TripArtifact.checkIn).fetch()
        for artifact in artifacts:
            if (artifact.type.lower=="plane") and (artifact.checkIn-datetime.now() <= timedelta(hours=24)):
                data = json.dumps({""})
                date = artifact.checkIn.split("/")
                req_url = "https://api.flightstats.com/flex/flightstatus/v2/json/flight/status?appId="+APP_ID+"&appKey=+"+API_KEY+"&carrier="+artifact.company+"&flight="+artifact.reservationNo+"&year="+date[2]+"&month"+date[0]+"&day="+date[1]
                req = urllib2.Request(req_url, data, {'Content-Type': 'application/json'})
                f = urllib2.urlopen(req)
                response = f.read()
                f.close()
                status = json.loads(response)
                digest = status["status"]+" \n"+status["departureDate"]+" \n"+status["irregularOperations"]
                trip = Trip.get_by_id(artifact.parentTrip)
                for email in trip.travelers:            
                    send_mail("",[email.userId],"Voyage With US Notification","Your flight %s for trip %s has updates %s"%(artifact.reservationNo, trip.name, digest))            
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(response))

class UpdateJob(webapp2.RequestHandler):
    def get(self):
        #TODO - send phone notifications
        return

application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/sharetrip', ShareTrip),
    ('/jointrip', JoinTrip),
    ('/leavetrip', LeaveTrip),
    ('/subscribe', Subscribe),
    ('/unsubscribe', Unsubscribe),
    ('/imageupload', UploadImage),
    ('/upload',BlobUpload),
    ('/reporting', ReportingPreferences),
    ('/flightupdate',FlightUpdate),
    ('/tripupdate',UpdateJob),
    ('/trips', AllTrips),
    ('/trips/(.*)', Trips),
    ('/trips/users/(.*)', UserTrips),
    ('/trips/users/(.*)/current', CurrentTrips),
    ('/trips/users/(.*)/past', PastTrips),
    ('/artifacts/(.*)', Artifacts),
    ('/trips/(.*)/artifacts',TripArtifacts),
    ('/users', CreateUsers),
    ('/users/(.*)', Users),
    ('/sentiments', Sentiments),
    ('/sentiments/pois/(.*)', SentimentsPois),
    ('/sentiments/users/(.*)', SentimentsUsers),
    ('/pois', AllPois),
    ('/pois/(.*)', Pois),
    ('/recommend/trip/(.*)', RecommendTrip),
    ('/recommend/nearby', RecommendNearby),
    ('/itinerary/trip/(.*)', ItineraryTrip),
    ('/itinerary/walking/trip/(.*)', RecommendNearby)
], debug=True)