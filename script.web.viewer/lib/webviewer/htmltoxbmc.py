import re
import htmlentitydefs

'''
TODO:
'''
class HTMLConverter:
	def __init__(self):
		self.ordered = False
		self.bullet = unichr(8226)
		self.tdSeperator = ' %s ' % self.bullet
		
		self.formColorA = 'FF010256'
		self.formColorB = 'FF010250'
		self.formColorC = 'FF010257'
		
		self.linkColor = 'FF015602'
		self.imageColor = 'FF0102FE'
		
		self.frameColor = 'FF015642'
		#static replacements		
		#self.imageReplace = '[COLOR FFFF0000]I[/COLOR][COLOR FFFF8000]M[/COLOR][COLOR FF00FF00]G[/COLOR][COLOR FF0000FF]#[/COLOR][COLOR FFFF00FF]%s[/COLOR]: [I]%s[/I] '
		self.imageReplace = '[COLOR FFFF0000]I[/COLOR][COLOR FFFF8000]M[/COLOR][COLOR FF00FF00]G[/COLOR][COLOR '+self.imageColor+']#%s%s [/COLOR]'

#		self.linkReplace = unicode.encode('[CR]\g<text> (%s: [B]\g<url>[/B])' % u'Link','utf8')
		self.linkReplace = '[COLOR '+self.linkColor+']%s[/COLOR] '
		self.frameReplace = '[CR][COLOR '+self.frameColor+']FRAME%s[/COLOR][CR]'
		self.formReplace = '[CR][COLOR '+self.formColorA+']'+'_'*200+'[/COLOR][CR][COLOR '+self.formColorB+'][B]- FORM: %s -[/B][/COLOR][CR]%s[CR][COLOR '+self.formColorC+']'+'_'*200+'[/COLOR][CR][CR]'
		self.submitReplace = '[\g<value>] '
		#static filters
		self.linkFilter = re.compile('<(?:a|embed)[^>]+?(?:href|src)=["\'](?P<url>[^>"]+?)["\'][^>]*?(?:title=["\'](?P<title>[^>"]+?)["\'][^>]*?)?>(?P<text>.*?)</(?:a|embed)>',re.I|re.S|re.U)
		self.imageFilter = re.compile('<img[^>]+?src=["\'](?P<url>[^>"]+?)["\'][^>]*?>',re.I|re.S|re.U)
		self.scriptFilter = re.compile('<script[^>]*?>.*?</script>',re.S|re.I)
		self.styleFilter = re.compile('<style[^>]*?>.+?</style>',re.I)
		self.commentFilter = re.compile('<!.*?-->')
		self.formFilter = re.compile('<form[^>]*?(?:id=["\'](?P<id>[^>"]+?)["\'][^>]*?)?>(?P<contents>.+?)(?:</form>|<form>|$)(?is)')
		self.labelFilter = re.compile('<label[^>]*?(?:(?:for=["\'])|(?:>\s*<input[^>]*?id="))(?P<inputid>[^>"].*?)["\'][^>]*?>(?P<label>.*?)</label>',re.I)
		self.altLabelFilter = re.compile('>(?:(?P<header>[^<>]*?)<(?!input|select)\w+[^>]*?>)?(?P<label>[^<>]+?)(?:<(?!input|select)\w+[^>]*?>)?(?:<input |<select )[^>]*?(?:id|name)="(?P<inputid>[^>"]+?)"',re.I)
		self.submitFilter = re.compile('<input type=["\']submit["\'][^>]+?value=["\'](?P<value>[^>"\']+?)["\'][^>]*?>',re.I)
		self.lineItemFilter = re.compile('<(li|/li|ul|ol|/ul|/ol)[^>]*?>',re.I)
		self.ulFilter = re.compile('<ul[^>]*?>(.+?)</ul>',re.I)
		self.olFilter = re.compile('<ol[^>]*?>(.+?)</ol>',re.I)
		self.brFilter = re.compile('<br[^>]*/{0,1}>',re.I)
		self.blockQuoteFilter = re.compile('<blockquote>(.+?)</blockquote>',re.S|re.I)
		self.colorFilter = re.compile('<font color="([^>"]+?)">(.+?)</font>',re.I)
		self.colorFilter2 = re.compile('<span[^>]*?style="[^>"]*?color: ?([^>]+?)"[^>]*?>(.+?)</span>',re.I)
		self.tagString = '<[^!][^>]*?>'
		interTagWSString = '(%s)\s*(%s)' % (self.tagString,self.tagString)
		self.tagFilter = re.compile(self.tagString,re.S|re.I)
		self.interTagWSFilter = re.compile(interTagWSString,re.I)
		self.lineFilter = re.compile('[\n\r]')
		self.tabFilter = re.compile('\t')
		self.titleFilter = re.compile('<title>(.+?)</title>',re.I)
		self.bodyFilter = re.compile('<body[^>]*?>(.+)</body>',re.S|re.I)
		self.frameFilter = re.compile('<i?frame[^>]*?src="(?P<url>[^>"]+?)"[^>]*?>(?:.*?</iframe>)?',re.I)
		self.noframesFilter = re.compile('<noframes>.*?</noframes>',re.I)
		
		self.idFilter = re.compile('<[^>]+?(?:id|name)="([^>"]+?)"[^>]*?>',re.S|re.I)
		
		self.displayTagFilter = re.compile('\[/?(?:(?:COLOR(?: [^\]]*?)?)|B|I)\]')
		
		#Secondary Filters
		self.lineItemLineFilter = re.compile('<li[^>]*?>(.+?)</li>',re.I)
		self.imageAltFilter = re.compile('alt="([^"]+?)"',re.I)
		self.titleAttrFilter = re.compile('title="([^>"]*?)"',re.I)
		self.nameAttrFilter = re.compile('name="([^>"]*?)"',re.I)
		self.boldStartFilter = re.compile('<b(?: [^>]*?)?>',re.I)
		self.italicsStartFilter = re.compile('<i(\s[^>]*?)?>',re.I)
		self.strongStartFilter = re.compile('<strong[^>]*?>',re.I)
		self.headerStartFilter = re.compile('<h\d[^>]*?>',re.I)
		self.headerEndFilter = re.compile('</h\d>',re.I)
		self.emStartFilter = re.compile('<em(\s[^>]*?)?>',re.I)
		self.tableStartFilter = re.compile('<table[^>]*?>',re.I)
		
		self.headTagEndFilter = re.compile('</head>',re.I)
		self.leadingTrailingWSFilter = re.compile('\s*([\n\r])\s*')
		self.lineReduceFilter = re.compile('\n+')
		
		self.eolWhitspaceFilter = re.compile('\s+(?=\[CR\])',re.U)
		self.lessEolFilter = re.compile('(?:\[CR\]){2,}')
		
	def htmlToDisplay(self,html):
		if not html: return 'NO PAGE','NO PAGE'
		if type(html) != type(u''): html = unicode(html,'utf8','replace')
		try:
			title = self.titleFilter.search(html).group(1)
		except:
			title = ''
		
		html = self.cleanHTML(html)
		
		self.imageCount = 0
		self.imageDict = {}
		
		html = self.linkFilter.sub(self.linkConvert,html)
		html = self.imageFilter.sub(self.imageConvert,html)
		html = self.formFilter.sub(self.formConvert,html)
		html = self.submitFilter.sub(self.submitReplace,html)
		html = self.frameFilter.sub(self.frameConvert,html)
		html = self.noframesFilter.sub('',html)
		html = self.styleFilter.sub('',html)
		
		html = self.processLineItems(html)
		
		
		html = self.colorFilter.sub(self.convertColor,html)
		html = self.colorFilter2.sub(self.convertColor,html)
		html = self.brFilter.sub('[CR]',html)
		html = self.blockQuoteFilter.sub(self.processIndent,html)
		html = self.boldStartFilter.sub('[B]',html).replace('</b>','[/B]')
		html = self.italicsStartFilter.sub('[I]',html).replace('</i>','[/I]')
		html = html.replace('<u>','_').replace('</u>','_')
		html = self.strongStartFilter.sub('[B]',html).replace('</strong>','[/B]')
		html = self.headerStartFilter.sub('[CR][CR][B]',html)
		html = self.headerEndFilter.sub('[/B][CR][CR]',html)
		html = self.emStartFilter.sub('[I]',html).replace('</em>','[/I]')
		html = self.tableStartFilter.sub('[CR]',html)
		html = html.replace('</table>','[CR][CR]')
		html = html.replace('</div></div>','[CR]') #to get rid of excessive new lines
		html = html.replace('</div>','[CR]')
		html = html.replace('</p>','[CR][CR]')
		html = html.replace('</tr>','[CR][CR]')
		html = html.replace('</td><td>',self.tdSeperator)
		html = self.tagFilter.sub('',html)
		html = self.removeNested(html,'\[/?B\]','[B]')
		html = self.removeNested(html,'\[/?I\]','[I]')
		html = html.replace('[CR]','\n').strip().replace('\n','[CR]') #TODO: Make this unnecessary
		
		html = self.convertHTMLCodes(html)
		html = self.eolWhitspaceFilter.sub('',html)
		html = self.lessEolFilter.sub('[CR][CR]',html)
		#import codecs
		#codecs.open('/home/ruuk/test.txt','w',encoding='utf-8').write(html)
		
		return html,self.convertHTMLCodes(title)
	
	def cleanHTML(self,html):
		try:
			html = self.headTagEndFilter.split(html)[1]
			#html = self.bodyFilter.search(html).group(1)
		except:
			#print 'ERROR - Could not parse <body> contents'
			print 'ERROR - Could not find </head> tag'
		#html = self.lineFilter.sub(' ',html)
		html = self.tabFilter.sub('',html)
		#remove leading and trailing whitespace 
		html = self.leadingTrailingWSFilter.sub(r'\1',html)
		
		#Remove whitespace between tags
		html = self.interTagWSFilter.sub(r'\1\2',html)
		
		#Remove newlines from tags
		html = self.tagFilter.sub(self.cleanTags,html)
		#import codecs
		#codecs.open('/home/ruuk/test.txt','w',encoding='utf-8').write(html)
		
		html = self.lineReduce(html)
		#html = self.styleFilter.sub('',html)
		html = self.scriptFilter.sub('',html)
		html = self.commentFilter.sub('',html)
		return html
		
	def frameConvert(self,m):
		title = ''
		title_m = self.titleAttrFilter.search(m.group(0))
		if not title_m:
			title_m = self.nameAttrFilter.search(m.group(0))
		if title_m: title = ':%s' % title_m.group(1)
		return self.frameReplace % title
	
	def cleanTags(self,m):
		return self.lineFilter.sub('',m.group(0))
	
	def lineReduce(self,data):
		return self.lineReduceFilter.sub(' ',self.lineFilter.sub('\n',data))
	
	def formConvert(self,m):
		return self.formReplace % (m.group('id'),m.group('contents'))
	
	def htmlToDisplayWithIDs(self,html):
		html = unicode(html,'utf8','replace')
		html = self.idFilter.sub(r'\g<0>[{\g<1>}]',html)
		return self.htmlToDisplay(html)

	def getImageNumber(self,url):
		if url in self.imageDict: return self.imageDict[url]
		self.imageCount += 1
		self.imageDict[url] = self.imageCount
		return self.imageCount
	
	def processLineItems(self,html):
		self.indent = -1
		self.oIndexes = []
		self.ordered_count = 0
		self.lastLI = ''
		return self.lineItemFilter.sub(self.lineItemProcessor,html)
		
	def resetOrdered(self,ordered):
		self.oIndexes.append(self.ordered_count)
		self.ordered = ordered
		self.ordered_count = 0
		
	def lineItemProcessor(self,m):
		li_type = m.group(1)
		ret = ''
		if li_type == 'li':
			if self.lastLI == '/li' or self.lastLI == 'li' or not self.indent: ret = '\n'
			#if self.lastLI == 'ul' or self.lastLI == 'ol' or self.lastLI == '/ul' or self.lastLI == '/ol': ret = ''
			self.ordered_count += 1
			if self.ordered: bullet = str(self.ordered_count) + '.'
			else: bullet = self.bullet
			ret += '%s%s' % ('   ' * self.indent,bullet)
		#elif li_type == '/li':
		#	
		elif li_type == 'ul':
			self.indent += 1
			self.resetOrdered(False)
			ret = '\n'
		elif li_type == 'ol':
			self.indent += 1
			self.resetOrdered(True)
			ret = '\n'
		elif li_type == '/ul':
			self.indent -= 1
			self.ordered_count = self.oIndexes.pop()
		elif li_type == '/ol':
			self.indent -= 1
			self.ordered_count = self.oIndexes.pop()
		self.lastLI = li_type
		return ret
		
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
		am = self.imageAltFilter.search(m.group(0))
		alt = am and am.group(1) or ''
		alt = alt and ':' + alt or ''
		return self.imageReplace % (self.getImageNumber(m.group(1)),alt)
		#return self.imageReplace % (self.imageCount,m.group('url'))

	def linkConvert(self,m):
		text = m.group('text')
		if '<img' in text:
			am = self.imageAltFilter.search(text)
			if am:
				text = am.group(1) or 'LINK'
			else:
				text = self.imageFilter.sub('',text)
				text += 'LINK'
		elif not text:
			text = m.groupdict().get('title','LINK')
		#print 'x%sx' % unicode.encode(text,'ascii','replace')
		return self.linkReplace % text
	
	def processIndent(self,m):
		return '    ' + m.group(1).replace('\n','\n    ') + '\n'
		
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
		return self.lineItemLineFilter.sub(self.processItem,html) + '\n'

	def processItem(self,m):
		self.ordered_count += 1
		if self.ordered: bullet = str(self.ordered_count) + '.'
		else: bullet = '*'
		return  '%s %s\n' % (bullet,m.group(1))
	
	def convertHTMLCodes(self,html):
		return convertHTMLCodes(html)

charCodeFilter = re.compile('&#(\d{1,5});',re.I)
charNameFilter = re.compile('&(\w+?);')
		
def cUConvert(m): return unichr(int(m.group(1)))
def cTConvert(m):
	return unichr(htmlentitydefs.name2codepoint.get(m.group(1),32))
	
def convertHTMLCodes(html):
	try:
		html = charCodeFilter.sub(cUConvert,html)
		html = charNameFilter.sub(cTConvert,html)
	except:
		pass
	return html
	
