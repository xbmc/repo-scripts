import sys, re, textwrap, htmlentitydefs

DEBUG = sys.modules["__main__"].DEBUG
LOG = sys.modules["__main__"].LOG
ERROR = sys.modules["__main__"].ERROR
__addon__ = sys.modules["__main__"].__addon__
__language__ = sys.modules["__main__"].__language__
FB = sys.modules["__main__"].FB

def cUConvert(m): return unichr(int(m.group(1)))
def cTConvert(m): return unichr(htmlentitydefs.name2codepoint.get(m.group(1),32))
def convertHTMLCodes(html):
	if not isinstance(html,unicode):
		html = unicode(html,'utf8','replace')
	try:
		html = re.sub('&#(\d{1,5});',cUConvert,html)
		html = re.sub('&(\w+?);',cTConvert,html)
	except:
		pass
	return html
	
######################################################################################
# Message Converter
######################################################################################
class MessageConverter:
	
	tagFilter = re.compile('<[^<>]+?>',re.S)
	brFilter = re.compile('<br[ /]{0,2}>')
	
	def __init__(self,fb):
		global FB
		FB = fb
		self.fb = fb
		self._currentFilter = None
		self.resetOrdered(False)
		self.textwrap = textwrap.TextWrapper(80)
		
		#static filters
		self.imageFilter = re.compile('<img[^>]+src="(?P<url>http://[^"]+)"[^>]*/>')
		self.linkFilter = re.compile('<a.+?href="(?P<url>.+?)".*?>(?P<text>.+?)</a>')
		self.ulFilter = re.compile('<ul>(.+?)</ul>')
		#<span style="text-decoration: underline">Underline</span>
		self.olFilter = re.compile('<ol.+?>(.+?)</ol>')
		self.brFilter = re.compile('<br[ /]{0,2}>')
		self.blockQuoteFilter = re.compile('<blockquote>(.+?)</blockquote>',re.S)
		self.colorFilter = re.compile('<font color="(.+?)">(.+?)</font>')
		self.colorFilter2 = re.compile('<span.*?style=".*?color: ?(.+?)".*?>(.+?)</span>')
		self.setReplaces()
		self.resetRegex()
		
	def prepareSmileyList(self):
		class SmiliesList(list):
			def get(self,key,default=None): return default
			
		new = SmiliesList()
		if __addon__.getSetting('use_skin_mods') == 'true':
			for f,r,x in self.FB.smiliesDefs: #@UnusedVariable
				f = '(\s)'+ re.escape(f)
				if '[/COLOR]' in r:
					new.append((f,r))
				else:
					new.append((f,'[COLOR FFBBBB00]'+r+'[/COLOR]'))
		else:
			for f,r,x in self.FB.smiliesDefs: #@UnusedVariable
				f = '(\s)'+ re.escape(f)
				if '[/COLOR]' in x:
					new.append((f,x))
				else:
					new.append((f,'[COLOR FFBBBB00]'+x+'[/COLOR]'))
		self.FB.smilies = new
		
	def resetRegex(self):
		if not FB: return
		
		self.prepareSmileyList()

		self.lineFilter = re.compile('[\n\r\t]')
		f = FB.filters.get('quote')
		self.quoteFilter = f and re.compile(f) or None
		f = FB.filters.get('code')
		self.codeFilter = f and re.compile(f) or None
		f = FB.filters.get('php')
		self.phpFilter = f and re.compile(f) or None
		f = FB.filters.get('html')
		self.htmlFilter = f and re.compile(f) or None
		f = FB.smilies.get('regex')
		self.smileyFilter = f and re.compile(f) or None
		f = FB.filters.get('image')
		self.imageFilter = f and re.compile(f) or self.imageFilter
		f = FB.filters.get('link')
		self.linkFilter = f and re.compile(f) or self.linkFilter
		f = FB.filters.get('link2')
		self.linkFilter2 = f and re.compile(f) or None
		f = FB.getQuoteFormat()
		self.quoteFilter2 = f and re.compile(f) or None
		
		self.quoteStartFilter = re.compile(FB.getQuoteStartFormat())
		self.altQuoteStartFilter = re.compile(FB.altQuoteStartFilter)
		self.quoteEndFilter = re.compile('\[\/quote\](?i)')
		self.quoteEndOnLineFilter = re.compile('(?!<\n)\s*\[\/quote\](?i)')
		
		self.smileyReplace = '[COLOR '+FB.smilies.get('color','FF888888')+']%s[/COLOR]'
		
	def setReplaces(self):
		self.quoteReplace = unicode.encode('[CR]_________________________[CR][B]'+__language__(30180)+'[/B][CR]'+__language__(30181)+' [B]%s[/B][CR][I]%s[/I][CR]_________________________[CR][CR]','utf8')
		self.aQuoteReplace = unicode.encode('[CR]_________________________[CR][B]'+__language__(30180)+'[/B][CR][I]%s[/I][CR]_________________________[CR][CR]','utf8')
		self.quoteImageReplace = '[COLOR FFFF0000]I[/COLOR][COLOR FFFF8000]M[/COLOR][COLOR FF00FF00]A[/COLOR][COLOR FF0000FF]G[/COLOR][COLOR FFFF00FF]E[/COLOR]: \g<url>'
		self.imageReplace = '[COLOR FFFF0000]I[/COLOR][COLOR FFFF8000]M[/COLOR][COLOR FF00FF00]G[/COLOR][COLOR FF0000FF]#[/COLOR][COLOR FFFF00FF]%s[/COLOR]: [I]%s[/I] '
		self.linkReplace = unicode.encode('\g<text> (%s [B]\g<url>[/B])' % __language__(30182),'utf8')
		self.link2Replace = unicode.encode('(%s [B]\g<url>[/B])' % __language__(30182),'utf8')
		self.hrReplace = ('[B]_____________________________________________________________________________________[/B]').encode('utf8')
		
		if __addon__.getSetting('use_skin_mods') == 'true':
			self.quoteStartReplace = u'\u250c'+u'\u2500'*300+u'[CR][B]'+__language__(30180)+u' %s[/B]'
			self.quoteEndReplace = u'\u2514'+u'\u2500'*300+u'[CR]'
			self.quoteVert = u'\u2502'
			self.hrReplace = u'[B]'+u'\u2500'*300+u'[/B]'
			self.codeStartReplace = u'\u250c'+u'\u2500'*300
			self.codeEndReplace = u'\u2514'+u'\u2500'*300
			self.bullet = u'\u2022'
		else:
			self.quoteStartReplace = u','+u'-'*300+u'[CR][B]'+__language__(30180)+u' %s[/B]'
			self.quoteEndReplace = u'`'+u'-'*300+u'[CR]'
			self.quoteVert = u'|'
			self.hrReplace = u'[B]'+u'_'*300+u'[/B]'
			self.codeStartReplace = u','+u'-'*300
			self.codeEndReplace = u'`'+u'-'*300
			self.bullet = u'*'
			
		self.codeReplace = self.codeStartReplace + '[CR][B][COLOR FF999999]'+__language__(30183)+r'[/COLOR][/B][CR]%s[CR]' + self.codeEndReplace
		self.phpReplace = self.codeStartReplace + '[CR][B][COLOR FF999999]'+__language__(30184)+r'[/COLOR][/B][CR]%s[CR]' + self.codeEndReplace
		self.htmlReplace = self.codeStartReplace + '[CR][B][COLOR FF999999]'+__language__(30185)+r'[/COLOR][/B][CR]%s[CR]' + self.codeEndReplace
		
	def codeConvert(self,m):
		code = self.textwrap.fill(m.group(1).replace('[CR]','\n'))
		code = self.quoteVert + '[COLOR FF999999]' + code.replace('\n','\n[/COLOR]'+self.quoteVert+'[COLOR FF999999]') + '[/COLOR]'
		return self.codeStartReplace + '[CR]'+self.quoteVert+'[B]'+__language__(30183)+r'[/B][CR]%s[CR]' % code + self.codeEndReplace

	def phpConvert(self,m):
		code = self.textwrap.fill(m.group(1).replace('[CR]','\n'))
		code = self.quoteVert + '[COLOR FF999999]' + code.replace('\n','\n[/COLOR]'+self.quoteVert+'[COLOR FF999999]') + '[/COLOR]'
		return self.codeStartReplace + '[CR]'+self.quoteVert+'[B]'+__language__(30184)+r'[/B][CR]%s[CR]' % code + self.codeEndReplace
	
	def htmlConvert(self,m):
		code = self.textwrap.fill(m.group(1).replace('[CR]','\n'))
		code = self.quoteVert + '[COLOR FF999999]' + code.replace('\n','\n[/COLOR]'+self.quoteVert+'[COLOR FF999999]') + '[/COLOR]'
		return self.codeStartReplace + '[CR]'+self.quoteVert+'[B]'+__language__(30185)+r'[/B][CR]%s[CR]' % code + self.codeEndReplace
	
	def indentConvert(self,m):
		code = self.textwrap.fill(m.group(1).replace('[CR]','\n'))
		return '    ' + code.replace('\n','\n    ')
	
	def resetOrdered(self,ordered):
		self.ordered = ordered
		self.ordered_count = 0
		
	def messageToDisplay(self,html):
		#html = self.lineFilter.sub('',html)
		html = re.sub('[_]{10,}',r'\n\g<0>\n',html)
		html = html.replace('[hr]','\n[hr]\n')
		html = self.formatQuotes(html)
		html = re.sub('[_]{10,}',self.hrReplace,html) #convert the pre-converted [hr]
		#html = self.quoteStartFilter.sub(self.quoteConvert,html)
		#html = self.quoteEndFilter.sub(self.quoteEndReplace,html)
		#if self.quoteFilter: html = self.quoteFilter.sub(self.quoteConvert,html)
		#if self.quoteFilter2: html = self.quoteFilter2.sub(self.quoteConvert,html)
		if self.codeFilter: html = self.codeFilter.sub(self.codeReplace,html)
		if self.phpFilter: html = self.phpFilter.sub(self.phpReplace,html)
		if self.htmlFilter: html = self.htmlFilter.sub(self.htmlReplace,html)
		if self.smileyFilter: html = self.smileyFilter.sub(self.smileyConvert,html)
		
		self.imageCount = 0
		html = self.imageFilter.sub(self.imageConvert,html)
		html = self.linkFilter.sub(self.linkReplace,html)
		if self.linkFilter2: html = self.linkFilter2.sub(self.link2Replace,html)
		html = self.ulFilter.sub(self.processBulletedList,html)
		html = self.olFilter.sub(self.processOrderedList,html)
		html = self.colorFilter.sub(self.convertColor,html)
		html = self.colorFilter2.sub(self.convertColor,html)
		html = self.brFilter.sub('[CR]',html)
		html = self.blockQuoteFilter.sub(self.processIndent,html)
		html = html.replace('<b>','[B]').replace('</b>','[/B]')
		html = html.replace('<i>','[I]').replace('</i>','[/I]')
		html = html.replace('<u>','_').replace('</u>','_')
		html = html.replace('<strong>','[B]').replace('</strong>','[/B]')
		html = html.replace('<em>','[I]').replace('</em>','[/I]')
		html = html.replace('</table>','[CR][CR]')
		html = html.replace('</div></div>','[CR]') #to get rid of excessive new lines
		html = html.replace('</div>','[CR]')
		html = html.replace('[hr]',self.hrReplace)
		html = self.tagFilter.sub('',html)
		html = self.removeNested(html,'\[/?B\]','[B]')
		html = self.removeNested(html,'\[/?I\]','[I]')
		html = html.replace('[CR]','\n').strip().replace('\n','[CR]') #TODO Make this unnecessary
		html = self.processSmilies(html)
		return convertHTMLCodes(html)

	def formatQuotesOld(self,html):
		ct = 0
		ms = True
		me = True
		#2503
		while ms or me:
			ms = self.quoteStartFilter.search(html)
			me = self.quoteEndFilter.search(html)
			if ms:
				if me and ms.start() > me.start():
					rep = self.quoteEndReplace
					if ct == 1:
						rep += '[/COLOR]'
					elif ct > 1:
						if not ct % 2:
							rep += '[/COLOR][COLOR FF5555AA]'
						else:
							rep += '[/COLOR][COLOR FF55AA55]'
					html = self.quoteEndFilter.sub(rep,html,1)
					ct -= 1
				else:
					gd = ms.groupdict()
					rep = self.quoteStartReplace % (gd.get('user') or '')
					if ct == 0: rep = '[COLOR FF5555AA]' + rep
					elif ct > 0:
						if ct % 2:
							rep = '[/COLOR][COLOR FF55AA55]' + rep
						else:
							rep = '[/COLOR][COLOR FF5555AA]' + rep
					html = self.quoteStartFilter.sub(rep,html,1)
					ct += 1
			elif me:
				rep = self.quoteEndReplace
				if ct == 1: rep += '[/COLOR]'
				elif ct > 1:
					if not ct % 2:
						rep += '[/COLOR][COLOR FF5555AA]'
					else:
						rep += '[/COLOR][COLOR FF55AA55]'
				html = self.quoteEndFilter.sub(rep,html,1)
				ct -= 1
		return html
			
	def formatQuotes(self,html):
		if not isinstance(html,unicode): html = unicode(html,'utf8')
		ct = 0
		ms = None
		me = None
		vertL = []
		html = html.replace('[CR]','\n')
		html = html.replace('<br />','\n')
		html = self.quoteEndOnLineFilter.sub('\n[/quote]',html)
		html = re.sub(self.quoteStartFilter.pattern + '(?!\n)','\g<0>\n',html)
		lines = html.splitlines()
		out = ''
		justStarted = False
		oddVert = u'[COLOR FF55AA55]%s[/COLOR]' % self.quoteVert
		evenVert = u'[COLOR FF5555AA]%s[/COLOR]' % self.quoteVert
		
		for line in lines:
			if ct < 0: ct = 0
			ms = self.quoteStartFilter.search(line)
			startFilter = self.quoteStartFilter
			if not ms: me = self.quoteEndFilter.search(line) #dont search if we don't have to
			if ms:
				alts = self.altQuoteStartFilter.search(line)
				if alts:
					ms = alts
					startFilter = self.altQuoteStartFilter
				justStarted = True
				oldVert = ''.join(vertL)
				gd = ms.groupdict()
				rep = self.quoteStartReplace % (gd.get('user') or '')
				if ct == 0:
					rep = '[COLOR FF5555AA]' + rep
					vertL.append(evenVert)
				elif ct > 0:
					if ct % 2:
						rep = '[/COLOR][COLOR FF55AA55]' + rep
						vertL.append(oddVert)
					else:
						rep = '[/COLOR][COLOR FF5555AA]' + rep
						vertL.append(evenVert)
				vert = ''.join(vertL)
				out += oldVert + startFilter.sub(rep,line,1).replace('[CR]','[CR]' + vert) + '[CR]'
				ct += 1
			elif me:
				rep = self.quoteEndReplace
				if ct == 1: rep += '[/COLOR]'
				elif ct > 1:
					if not ct % 2:
						rep += '[/COLOR][COLOR FF5555AA]'
					else:
						rep += '[/COLOR][COLOR FF55AA55]'
				oldVert = ''.join(vertL)
				if vertL: vertL.pop()
				vert = ''.join(vertL)
				out += oldVert + self.quoteEndFilter.sub('[CR]' + rep,line,1).replace('[CR]','[CR]' + vert) + '[CR]'
				ct -= 1
			elif ct:
				if justStarted:
					out += vert + '[CR]'
				line = self.linkFilter.sub(r'\g<text> [B](Link)[/B]',line)
				if self.linkFilter2: line = self.linkFilter2.sub('[B](LINK)[/B]',line)
				wlines = self.textwrap.wrap(line)
				for l in wlines:
					out += vert + l + '[CR]'
			else:
				out += line + '[CR]'
			if not ms:
				justStarted = False
		return out
	
	def quoteConvert2(self,m):
		gd = m.groupdict()
		return self.quoteStartReplace % (gd.get('user') or '')
		
	def removeNested(self,html,regex,starttag):
		self.nStart = starttag
		self.nCounter = 0
		return re.sub(regex,self.nestedSub,html)
		
	def nestedSub(self,m):
		tag = m.group(0)
		if tag == self.nStart:
			self.nCounter += 1
			if self.nCounter == 1: return tag
		else:
			self.nCounter -= 1
			if self.nCounter < 0: self.nCounter = 0
			if self.nCounter == 0: return tag
		return ''
		
	def messageAsQuote(self,html):
		html = self.lineFilter.sub('',html)
		if self.quoteFilter: html = self.quoteFilter.sub('',html)
		if self.codeFilter: html = self.codeFilter.sub('[CODE]\g<code>[/CODE]',html)
		if self.phpFilter: html = self.phpFilter.sub('[PHP]\g<php>[/PHP]',html)
		if self.htmlFilter: html = self.htmlFilter.sub('[HTML]\g<html>[/HTML]',html)
		if self.smileyFilter: html = self.smileyFilter.sub(self.smileyConvert,html)
		html = self.linkFilter.sub('[URL="\g<url>"]\g<text>[/URL]',html)
		html = self.imageFilter.sub('[IMG]\g<url>[/IMG]',html)
		html = self.colorFilter.sub(self.convertColor,html)
		html = self.colorFilter2.sub(self.convertColor,html)
		html = html.replace('<b>','[B]').replace('</b>','[/B]')
		html = html.replace('<i>','[I]').replace('</i>','[/I]')
		html = html.replace('<u>','[U]').replace('</u>','[/U]')
		html = html.replace('<strong>','[B]').replace('</strong>','[/B]')
		html = html.replace('<em>','[I]').replace('</em>','[/I]')
		html = re.sub('<br[^<>]*?>','\n',html)
		html = html.replace('</table>','\n\n')
		html = html.replace('</div>','\n')
		html = re.sub('<[^<>]+?>','',html)
		return convertHTMLCodes(html).strip()
		
	def imageConvert(self,m):
		self.imageCount += 1
		return self.imageReplace % (self.imageCount,m.group('url'))

	def processSmilies(self,text):
		if not isinstance(text,unicode): text = unicode(text,'utf8')
		if self.smileyFilter: return text
		for f,r in self.FB.smilies: text = re.sub(f,r'\1'+r,text)
		return text
	
	def smileyRawConvert(self,m):
		return FB.smilies.get(m.group('smiley'),'')
		
	def smileyConvert(self,m):
		return self.smileyReplace % FB.smilies.get(m.group('smiley'),'')
		
	def quoteConvert(self,m):
		gd = m.groupdict()
		#quote = self.imageFilter.sub(self.quoteImageReplace,gd.get('quote',''))
		return self.quoteStartReplace % (gd.get('user') or '')
			
	def processIndent(self,m):
		return '    ' + re.sub('\n','\n    ',m.group(1)) + '\n'
		
	def convertColor(self,m):
		if m.group(1).startswith('#'):
			color = 'FF' + m.group(1)[1:].upper()
		else:
			color = m.group(1).lower()
		return '[COLOR %s]%s[/COLOR]' % (color,m.group(2))

	def processBulletedList(self,m):
		self.resetOrdered(False)
		return self.processList(m.group(1))
		
	def processOrderedList(self,m):
		self.resetOrdered(True)
		return self.processList(m.group(1))
			
	def processList(self,html):
		return re.sub('<li>(.+?)</li>',self.processItem,html) + '\n'

	def processItem(self,m):
		self.ordered_count += 1
		if self.ordered: bullet = str(self.ordered_count) + '.'
		else: bullet = '*'
		return  '%s %s\n' % (bullet,m.group(1))
		
	def parseCodes(self,text):
		text = re.sub('\[QUOTE=(?P<user>\w+)(?:;\d+)*\](?P<quote>.+?)\[/QUOTE\](?is)',self.quoteConvert,text)
		text = re.sub('\[QUOTE\](?P<quote>.+?)\[(?P<user>)?/QUOTE\](?is)',self.quoteConvert,text)
		text = re.sub('\[CODE\](?P<code>.+?)\[/CODE\](?is)',self.codeReplace,text)
		text = re.sub('\[PHP\](?P<php>.+?)\[/PHP\](?is)',self.phpReplace,text)
		text = re.sub('\[HTML\](?P<html>.+?)\[/HTML\](?is)',self.htmlReplace,text)
		text = re.sub('\[IMG\](?P<url>.+?)\[/IMG\](?is)',self.quoteImageReplace,text)
		text = re.sub('\[URL="?(?P<url>[^\]]+?)"?\](?P<text>.+?)\[/URL\](?is)',self.linkReplace,text)
		text = re.sub('\[URL\](?P<text>(?P<url>.+?))\[/URL\](?is)',self.link2Replace,text)
		return text

######################################################################################
# BBMessage Converter
######################################################################################
class BBMessageConverter(MessageConverter):
	def __init__(self,fb):
		self.FB = fb
		self.smileyFilter = None
		self._currentFilter = None
		self.textwrap = textwrap.TextWrapper(80)
		self.textwrap.replace_whitespace = False
		self.boldFilter = re.compile('\[(/?)b\]')
		self.italicsFilter = re.compile('\[(/?)i\]')
		self.indentFilter = re.compile('\[indent\](.*?)\[/indent\](?is)')
		self.sizeTagFilter = re.compile('\[/?size=?\d*\](?i)')
		self.numberedFilter = re.compile('\[list=\d\](.*?)\[/list\](?i)')
		self.bulletedFilter = re.compile('\[list\](.*?)\[/list\](?i)')
		self.kissingTagFilter = re.compile('(\[/\w+\])(\[\w+\])')
		self.listItemFilter = re.compile('\[\*\]')
		self.underlineFilter = re.compile('\[/?u\](?i)')
		self.setReplaces()
		self.resetRegex()
		
	def resetRegex(self):		
		self.prepareSmileyList()

		self.lineFilter = re.compile('[\n\r\t]')
		f = self.FB.filters.get('code')
		self.codeFilter = f and re.compile(f) or None
		f = self.FB.filters.get('php')
		self.phpFilter = f and re.compile(f) or None
		f = self.FB.filters.get('html')
		self.htmlFilter = f and re.compile(f) or None
		f = self.FB.filters.get('image')
		self.imageFilter = f and re.compile(f) or self.imageFilter
		f = self.FB.filters.get('link')
		self.linkFilter = f and re.compile(f) or self.linkFilter
		f = self.FB.filters.get('link2')
		self.linkFilter2 = f and re.compile(f) or None
		f = self.FB.filters.get('color_start')
		self.colorStart = f and re.compile(f) or None
		f = self.FB.getQuoteFormat()
		self.quoteFilter2 = f and re.compile(f) or None
		
		self.quoteStartFilter = re.compile(self.FB.getQuoteStartFormat())
		self.altQuoteStartFilter = re.compile(self.FB.altQuoteStartFilter)
		self.quoteEndFilter = re.compile('\[\/quote\](?i)')
		self.quoteEndOnLineFilter = re.compile('(?!<\n)\s*\[\/quote\](?i)')
		self.fakeHrFilter = re.compile('[_]{10,}')
		
	def messageToDisplay(self,html):
		#import codecs
		#codecs.open('test.txt','w','utf8').write(html)
		html = html.replace('[CR]','\n')
		html = self.kissingTagFilter.sub(r'\1\n\2',html)
		html = self.fakeHrFilter.sub(r'\n\g<0>\n',html)
		html = html.replace('[hr]','\n[hr]\n')
		html = self.formatQuotes(html)
		html = self.fakeHrFilter.sub(self.hrReplace,html) #convert the pre-converted [hr]
		
		html = self.boldFilter.sub(r'[\1B]',html)
		html = self.italicsFilter.sub(r'[\1I]',html)
		
		if self.codeFilter: html = self.codeFilter.sub(self.codeConvert,html)
		if self.phpFilter: html = self.phpFilter.sub(self.phpConvert,html)
		if self.htmlFilter: html = self.htmlFilter.sub(self.htmlConvert,html)
		html = self.indentFilter.sub(self.indentConvert,html)
		html = self.sizeTagFilter.sub('',html)
		
		if self.colorStart: html = self.colorStart.sub(r'[COLOR FF\1]',html)
		html = html.replace('[/color]','[/COLOR]')
		
		self.imageCount = 0
		html = self.imageFilter.sub(self.imageConvert,html)
		html = self.linkFilter.sub(self.linkReplace,html)
		if self.linkFilter2: html = self.linkFilter2.sub(self.link2Replace,html)
		html = html.replace('[hr]',self.hrReplace)
		html = self.removeNested(html,'\[/?B\]','[B]')
		html = self.removeNested(html,'\[/?I\]','[I]')
		html = self.underlineFilter.sub('_',html)
		html = self.bulletedFilter.sub(self.processBulletedList,html)
		html = self.numberedFilter.sub(self.processOrderedList,html)
		#html = html.replace('[CR]','\n').strip().replace('\n','[CR]') #TODO Make this unnecessary
		html = self.processSmilies(html)
		return convertHTMLCodes(html)
			
	def formatQuotes(self,html):
		if not isinstance(html,unicode): html = unicode(html,'utf8')
		ct = 0
		ms = None
		me = None
		vertL = []
		html = html.replace('[CR]','\n')
		html = html.replace('<br />','\n')
		html = self.quoteEndOnLineFilter.sub('\n[/quote]',html)
		html = self.altQuoteStartFilter.sub(r"[quote='\1']",html)
		html = re.sub(self.quoteStartFilter.pattern + '(?!\n)','\g<0>\n',html)
		lines = html.splitlines()
		out = ''
		justStarted = False
		oddVert = u'[COLOR FF55AA55]%s[/COLOR]' % self.quoteVert
		evenVert = u'[COLOR FF5555AA]%s[/COLOR]' % self.quoteVert
		
		for line in lines:
			if ct < 0: ct = 0
			ms = self.quoteStartFilter.search(line)
			startFilter = self.quoteStartFilter
			if not ms: me = self.quoteEndFilter.search(line) #dont search if we don't have to
			if ms:
				justStarted = True
				oldVert = ''.join(vertL)
				gd = ms.groupdict()
				rep = self.quoteStartReplace % (gd.get('user') or '')
				if ct == 0:
					rep = '[COLOR FF5555AA]' + rep
					vertL.append(evenVert)
				elif ct > 0:
					if ct % 2:
						rep = '[/COLOR][COLOR FF55AA55]' + rep
						vertL.append(oddVert)
					else:
						rep = '[/COLOR][COLOR FF5555AA]' + rep
						vertL.append(evenVert)
				vert = ''.join(vertL)
				out += oldVert + startFilter.sub(rep,line,1).replace('[CR]','[CR]' + vert) + '[CR]'
				ct += 1
			elif me:
				rep = self.quoteEndReplace
				if ct == 1: rep += '[/COLOR]'
				elif ct > 1:
					if not ct % 2:
						rep += '[/COLOR][COLOR FF5555AA]'
					else:
						rep += '[/COLOR][COLOR FF55AA55]'
				oldVert = ''.join(vertL)
				if vertL: vertL.pop()
				vert = ''.join(vertL)
				out += oldVert + self.quoteEndFilter.sub('[CR]' + rep,line,1).replace('[CR]','[CR]' + vert) + '[CR]'
				ct -= 1
			elif ct:
				if justStarted:
					out += vert + '[CR]'
				line = self.linkFilter.sub(r'\g<text> [B](Link)[/B]',line)
				line = re.sub('\[code\](?i)','__________\nCODE:\n',line)
				line = re.sub('\[/code\](?i)','\n__________',line)
				line = re.sub('\[php\](?i)','__________\nPHP:\n',line)
				line = re.sub('\[/php\](?i)','\n__________',line)
				line = re.sub('\[html\](?i)','__________\nHTML:\n',line)
				line = re.sub('\[/html\](?i)','\n__________',line)
				if self.linkFilter2: line = self.linkFilter2.sub('[B](LINK)[/B]',line)
				wlines = self.textwrap.fill(line).splitlines()
				for l in wlines:
					out += vert + l + '[CR]'
			else:
				out += line + '[CR]'
			if not ms:
				justStarted = False
		return out
	
	def processList(self,html):
		return self.listItemFilter.sub(self.processItem,html)
	
	def processItem(self,m):
		self.ordered_count += 1
		if self.ordered: bullet = str(self.ordered_count) + '. '
		else: bullet = self.bullet + ' '
		return  bullet

	def removeNested(self,html,regex,starttag):
		self.nStart = starttag
		self.nCounter = 0
		return re.sub(regex,self.nestedSub,html)
		
	def nestedSub(self,m):
		tag = m.group(0)
		if tag == self.nStart:
			self.nCounter += 1
			if self.nCounter == 1: return tag
		else:
			self.nCounter -= 1
			if self.nCounter < 0: self.nCounter = 0
			if self.nCounter == 0: return tag
		return ''
	
	def imageConvert(self,m):
		self.imageCount += 1
		return self.imageReplace % (self.imageCount,m.group('url'))
		
	def parseCodes(self,text):
		text = re.sub('\[QUOTE=(?P<user>\w+)(?:;\d+)*\](?P<quote>.+?)\[/QUOTE\](?is)',self.quoteConvert,text)
		text = re.sub('\[QUOTE\](?P<quote>.+?)\[(?P<user>)?/QUOTE\](?is)',self.quoteConvert,text)
		text = re.sub('\[CODE\](?P<code>.+?)\[/CODE\](?is)',self.codeReplace,text)
		text = re.sub('\[PHP\](?P<php>.+?)\[/PHP\](?is)',self.phpReplace,text)
		text = re.sub('\[HTML\](?P<html>.+?)\[/HTML\](?is)',self.htmlReplace,text)
		text = re.sub('\[IMG\](?P<url>.+?)\[/IMG\](?is)',self.quoteImageReplace,text)
		text = re.sub('\[URL="?(?P<url>[^\]]+?)"?\](?P<text>.+?)\[/URL\](?is)',self.linkReplace,text)
		text = re.sub('\[URL\](?P<text>(?P<url>.+?))\[/URL\](?is)',self.link2Replace,text)
		return text
	
######################################################################################
# Functions
######################################################################################

def subTags(m): return '[%s]' % m.group(1).upper()

#def translateDisplay(message):
#	pre = re.sub('\[(/?(?:(?:COLOR(?: \w+)?)|CR|B|I))\]',r'<\1>',message).replace('> ','><space>').replace(' <','<space><')
#	message = TR.translate(pre,FB.formats.get('language','en'),getLanguage(),newline='<CR>',format='html')
#	message = convertHTMLCodes(message)
#	message = message.replace('> ','>').replace(' <','<').replace('<space>',' ')
#	message = re.sub('<(/?COLOR(?: \w+)?)>',r'[\1]',message)
#	message = re.sub('<([^<>]+?)>',subTags,message)
#	return message
		
def calculatePage(low,high,total):
	low = int(low.replace(',',''))
	high = int(high.replace(',',''))
	total = int(total.replace(',',''))
	if high == total: return -1
	return str(int(round(float(high)/((high-low)+1))))