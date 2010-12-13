import urllib, simplejson

class googleTranslateAPI:
	base_url = 'https://ajax.googleapis.com/ajax/services/language/translate?v=1.0&q=%(query)s&langpair=%(from)s%%7C%(to)s'
	maxlen = 1800
	def createQuery(self,kwargs):
		if kwargs: return '&' + urllib.urlencode(kwargs)
		return ''
		
	def translate(self,string,langfrom,langto,newline='\n',**kwargs):
		if len(langfrom) > 2: langto = self.getLanguage(langfrom)
		if len(langto) > 2: langto = self.getLanguage(langto)
		nlrep = ' %s ' % newline
		if len(urllib.quote(string)) > self.maxlen:
			curr = ''
			quotes = []
			for q in string.split(newline):
				q += nlrep
				if len(urllib.quote(curr + q)) < self.maxlen:
					curr += q
				elif not curr:
					if len(urllib.quote(q)) < self.maxlen:
						quotes.append(q)
					else:
						import math
						f = lambda v, l: [v[i*l:(i+1)*l] for i in range(int(math.ceil(len(v)/float(l))))]
						for qq in f(q,self.maxlen): quotes.append(qq)
				else:
					quotes.append(curr)
					curr = q
			quotes.append(curr)
				
		else:
			quotes = [string]
			
		out = ''
		for q in quotes:
			url = self.base_url % {'query':urllib.quote(q),'from':langfrom,'to':langto} + self.createQuery(kwargs)
			search_results = urllib.urlopen(url)
			data = search_results.read()
			json = None
			try:
				json = simplejson.loads(data)
			except:
				print data
				raise
			search_results.close()
			res = json['responseData']
			out += res['translatedText']
		out += nlrep + 'Translation powered by Google'
		return out.replace(nlrep,newline)
		
	def getLanguage(self,lang):
		languages = {
			'AFRIKAANS' : 'af',
			'ALBANIAN' : 'sq',
			'AMHARIC' : 'am',
			'ARABIC' : 'ar',
			'ARMENIAN' : 'hy',
			'AZERBAIJANI' : 'az',
			'BASQUE' : 'eu',
			'BELARUSIAN' : 'be',
			'BENGALI' : 'bn',
			'BIHARI' : 'bh',
			'BRETON' : 'br',
			'BULGARIAN' : 'bg',
			'BURMESE' : 'my',
			'CATALAN' : 'ca',
			'CHEROKEE' : 'chr',
			'CHINESE' : 'zh',
			'CHINESE_SIMPLIFIED' : 'zh-CN',
			'CHINESE_TRADITIONAL' : 'zh-TW',
			'CORSICAN' : 'co',
			'CROATIAN' : 'hr',
			'CZECH' : 'cs',
			'DANISH' : 'da',
			'DHIVEHI' : 'dv',
			'DUTCH': 'nl',  
			'ENGLISH' : 'en',
			'ESPERANTO' : 'eo',
			'ESTONIAN' : 'et',
			'FAROESE' : 'fo',
			'FILIPINO' : 'tl',
			'FINNISH' : 'fi',
			'FRENCH' : 'fr',
			'FRISIAN' : 'fy',
			'GALICIAN' : 'gl',
			'GEORGIAN' : 'ka',
			'GERMAN' : 'de',
			'GREEK' : 'el',
			'GUJARATI' : 'gu',
			'HAITIAN_CREOLE' : 'ht',
			'HEBREW' : 'iw',
			'HINDI' : 'hi',
			'HUNGARIAN' : 'hu',
			'ICELANDIC' : 'is',
			'INDONESIAN' : 'id',
			'INUKTITUT' : 'iu',
			'IRISH' : 'ga',
			'ITALIAN' : 'it',
			'JAPANESE' : 'ja',
			'JAVANESE' : 'jw',
			'KANNADA' : 'kn',
			'KAZAKH' : 'kk',
			'KHMER' : 'km',
			'KOREAN' : 'ko',
			'KURDISH': 'ku',
			'KYRGYZ': 'ky',
			'LAO' : 'lo',
			'LATIN' : 'la',
			'LATVIAN' : 'lv',
			'LITHUANIAN' : 'lt',
			'LUXEMBOURGISH' : 'lb',
			'MACEDONIAN' : 'mk',
			'MALAY' : 'ms',
			'MALAYALAM' : 'ml',
			'MALTESE' : 'mt',
			'MAORI' : 'mi',
			'MARATHI' : 'mr',
			'MONGOLIAN' : 'mn',
			'NEPALI' : 'ne',
			'NORWEGIAN' : 'no',
			'OCCITAN' : 'oc',
			'ORIYA' : 'or',
			'PASHTO' : 'ps',
			'PERSIAN' : 'fa',
			'POLISH' : 'pl',
			'PORTUGUESE' : 'pt',
			'PORTUGUESE_PORTUGAL' : 'pt-PT',
			'PUNJABI' : 'pa',
			'QUECHUA' : 'qu',
			'ROMANIAN' : 'ro',
			'RUSSIAN' : 'ru',
			'SANSKRIT' : 'sa',
			'SCOTS_GAELIC' : 'gd',
			'SERBIAN' : 'sr',
			'SINDHI' : 'sd',
			'SINHALESE' : 'si',
			'SLOVAK' : 'sk',
			'SLOVENIAN' : 'sl',
			'SPANISH' : 'es',
			'SUNDANESE' : 'su',
			'SWAHILI' : 'sw',
			'SWEDISH' : 'sv',
			'SYRIAC' : 'syr',
			'TAJIK' : 'tg',
			'TAMIL' : 'ta',
			'TATAR' : 'tt',
			'TELUGU' : 'te',
			'THAI' : 'th',
			'TIBETAN' : 'bo',
			'TONGA' : 'to',
			'TURKISH' : 'tr',
			'UKRAINIAN' : 'uk',
			'URDU' : 'ur',
			'UZBEK' : 'uz',
			'UIGHUR' : 'ug',
			'VIETNAMESE' : 'vi',
			'WELSH' : 'cy',
			'YIDDISH' : 'yi',
			'YORUBA' : 'yo',
			'UNKNOWN' : ''
		}
		return languages.get(lang.upper(),'')
