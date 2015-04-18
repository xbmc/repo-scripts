import default
reload(default)
from default import newGraph, FacebookUser, LOG, ERROR
fbLOG = LOG
import xbmcgui, xbmcaddon #@UnresolvedImport
from urllib2 import HTTPError

import ShareSocial #@UnresolvedImport

__addon__ = xbmcaddon.Addon(id='script.facebook.media')

def getCurrentUser():
	uid = __addon__.getSetting('current_user')
	if not uid:
		ulist = getUserList()
		if ulist:
			uid = ulist[0]
	if not uid: return None
	return FacebookUser(uid)

def getUserList():
	ustring = __addon__.getSetting('user_list')
	if not ustring: return []
	return ustring.split(',')

def selectAlbum(graph,share):
	albums = graph.getObject('me').connections.albums()
	menu = share.getOptionsMenu()
	for a in albums:
		menu.addItem(a.id,a.name(''))
	return menu.getResult()

def doShareSocial():
	return FacebookTargetFunctions()

class FacebookTargetFunctions(ShareSocial.TargetFunctions):
	def __init__(self):
		self.graph = None
		user = getCurrentUser()
		if not user: return
		self.newGraph(user)
		
	def newGraph(self,user):
		if not user: return self.graph
		if not isinstance(user,FacebookUser): user = FacebookUser(user)
		if self.graph and self.graph.uid == user.id: return self.graph
		self.graph = newGraph(	user.email,
								user.password(),
								user.id,
								user.token,
								user.updateToken)
		return self.graph
	
	def getUsers(self,share=None):
		users = getUserList()
		ulist = []
		for ID in users:
			user = FacebookUser(ID)
			ulist.append({'id':ID,'name':user.username,'photo':user.pic})
		return ulist
			
	def getFeedComments(self,commsObj):
		postID = commsObj.callbackDict.get('id')
		post = self.graph.getObject(postID)
		commsObj.clear()
		for c in post.connections.comments():
			userimage = 'http://graph.facebook.com/%s/picture'  % c.from_().get('id')
			commsObj.addItem(c.from_().get('name'),userimage,c.message(''),c.created_time())
		return commsObj
	
	def provide(self,getObject,ID=None):
		graph = self.newGraph(ID)
		if not graph: return getObject.error('NOUSERS')
		
		user = FacebookUser(ID or graph.uid)
		user = {'id':user.id,'name':user.username,'photo':user.pic}
		
		if getObject.type == 'feed':
			fbLOG('Providing feed to ShareSocial')
			feed = graph.getObject('me').connections.home()
			for f in feed:
				#print f._data
				msg = []
				if f.name(): msg.append(f.name())
				if f.message(): msg.append(f.message())
				if f.caption(): msg.append(f.caption())
				if f.description(): msg.append(f.description())
				#print f.application()
				commsObj = getObject.getCommentsList()
				comments = f.comments()
				if isinstance(comments,list):
					for c in comments:
						uimage = 'http://graph.facebook.com/%s/picture'  % c.from_().get('id')
						commsObj.addItem(c.from_().get('name'),uimage,c.message(''),c.created_time())
						commsObj.count = comments.count
						commsObj.callbackDict['id'] = f.id
				elif comments:
					commsObj.count = comments.get('count',0)
					commsObj.callbackDict['id'] = f.id
				pic = f.picture('')
				if True: #not pic:
					if f.type() == 'photo':
						obj_id = f.get('object_id')
						if obj_id:
							#print 'test: %s' % obj_id
							try:
								pic = graph.getObject(obj_id).source('')
							except Exception, e:
								print fbLOG('ERROR: %s' % e.message)
								
				userimage = 'http://graph.facebook.com/%s/picture' % f.from_().get('id')
				share = self.createShareFromPost(f)
				getObject.addItem(f.from_().get('name'),userimage,' - '.join(msg),f.created_time(),pic,comments=commsObj,share=share,client_user=user)
			return getObject
		
		elif getObject.type == 'imagestream':
			photos = self.graph.getObject('me').connections.photos__uploaded()
			shares = []
			for p in photos:
				share = ShareSocial.getShare('script.facebook.media',  'image')
				share.name = 'Facebook Media'
				share.title = p.name('')
				share.page = p.link('')
				share.thumbnail = p.icon('')
				share.media = p.source('')
				obj_id = p.id
				if not obj_id:
					continue
				share.callbackData = obj_id
				shares.append(share)
			return shares
		
	def getShareData(self,share):
		obj_id = share.callbackData
		obj = self.graph.getObject(obj_id)
		share.page = obj.link('')
		if share.shareType == 'image':
			share.media = obj.source('')
			share.title = obj.name('')
			share.thumbnail = obj.picture()
		return share
			
	def createShareFromPost(self,post):
		if post.type() == 'photo':
			share = ShareSocial.getShare('script.facebook.media','image')
			share.name = 'Facebook Media'
			share.title = 'Facebook Media Photo'
			share.page = post.link('')
			share.thumbnail = post.picture()
			obj_id = post.get('object_id')
			if not obj_id: return None
			share.callbackData = obj_id
			return share
		elif post.type() == 'video':
			share = ShareSocial.getShare('script.facebook.media','video')
			share.name = 'Facebook Media'
			share.title = 'Facebook Media Video'
			share.page = post.link('')
			share.swf = post.source('')
			share.thumbnail = post.picture()
			obj_id = post.get('object_id')
			if not obj_id: return None
			share.callbackData = obj_id
			return share
		elif post.type() == 'link':
			share = ShareSocial.getShare('script.facebook.media','link')
			share.name = 'Facebook Media'
			share.title = 'Facebook Media Link'
			share.page = post.link('')
			share.thumbnail = post.picture()
			return share
		elif post.source():
			share = ShareSocial.getShare('script.facebook.media','video')
			share.name = 'Facebook Media'
			share.title = 'Facebook Media Video'
			share.page = post.link('')
			share.swf = post.source('')
			share.thumbnail = post.picture()
			return share
		return None
		
	def share(self,share,ID=None):
		graph = self.newGraph(ID)
		
		if not share.shareType == 'status': share.askMessage()
		
		if share.shareType == 'image':
			attachement = {	"name": share.title,
							"link": share.link(),
							"caption": "Shared From XBMC",
							"description": share.message,
							"picture": share.thumbnail }
			fbLOG('Sharing: Posting %s to wall' % share.shareType)
			graph.putWallPost(share.title, attachment=attachement)
			return share.succeeded()
		elif share.shareType == 'video' or share.shareType == 'audio':
			attachement = {	"name": share.title,
							"link": share.link(),
							"caption": "Shared From XBMC",
							"description": share.message,
							"picture": share.thumbnail,
							"source": share.swf or share.media}
			fbLOG('Sharing: Posting %s to wall' % share.shareType)
			graph.putWallPost(share.title, attachment=attachement)
			return share.succeeded()
		elif share.shareType == 'imagefile':
			share.progressCallback(0,1,'Select Album...',hide=True)
			aid = selectAlbum(graph,share)
			if not aid: return share.failed('No album selected')
			
			try:	
				share.progressCallback(0,1,'Waiting for Facebook...',hide=False)
				graph.putObject(aid, 'photos',title=share.title,message=share.message,source=open(share.media))
				return share.succeeded()
			except:
				ERROR('ShareSocial: Image upload failed.')
				return share.failed('Image upload Failed')
			
		elif share.shareType == 'videofile':
			#http://developers.facebook.com/blog/post/493/
			#The aspect ratio of the video must be between 9x16 and 16x9, and the video cannot exceed 1024MB or 180 minutes in length.
			try:	
				share.progressCallback(0,1,'Getting user info...')
				user = graph.getObject('me',fields='id,name')
				share.progressCallback(0,1,'Waiting for Facebook...','Uploading to: %s' % user.name())
				#filename = os.path.basename(share.media)
				#print filename
				#print share.title
				graph.putObject('https://graph-video.facebook.com/me','videos',title=share.title,description=share.message,file=open(share.media))
				return share.succeeded()
			except HTTPError, e:
				if e.code == 400:
					reason = e.headers.get('WWW-Authenticate')
					ERROR('\nMessage: %s\nReason: %s' % (e.msg,reason))
					return share.failed(reason.split('" "')[-1][:-1],error=e)
			except:
				return ERROR('Video upload Failed')
		elif share.shareType == 'status':
			if not share.message: share.askMessage()
			graph.putWallPost(share.message)
			return share.succeeded()
		else:
			return share.failed('Cannot Share This Type') # This of course shoudn't happen
		
		return share.failed('Unknown Error') # This of course shoudn't happen