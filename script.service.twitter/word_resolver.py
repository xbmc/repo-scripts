import re
def lang(language):
	if language == 'All Languages':
		language = 'all'
		return language
	if language == 'English':
		language = 'en'
		return language
	if language == 'Arabic':
		language = 'ar'
		return language
	if language == 'Armenian' :
		language = 'am'
		return language
	if language == 'Bulgarian' :
		language = 'bg'
		return language
	if language == 'Chinese' :
		language = 'zh'
		return language
	if language == 'Danish' :
		language = 'da'
		return language
	if language == 'Dutch' :
		language = 'ni'
		return language
	if language == 'Finnish' :
		language = 'fi'
		return language
	if language == 'French' :
		language = 'fr'
		return language
	if language == 'Georgian' :
		language = 'ka'
		return language
	if language == 'German' :
		language = 'de'
		return language
	if language == 'Greek' :
		language = 'el'
		return language
	if language == 'Hebrew' :
		language = 'he'
		return language
	if language == 'Hungarian' :
		language = 'hu'
		return language
	if language == 'Icelandic' :
		language = 'is'
		return language
	if language == 'Indonesian' :
		language = 'id'
		return language
	if language == 'Inuktitut' :
		language = 'iu'
		return language
	if language == 'Italian' :
		language = 'it'
		return language
	if language == 'Japanese' :
		language = 'ja'
		return language
	if language == 'Korean' :
		language = 'ko'
		return language
	if language == 'Lao' :
		language = 'lo'
		return language
	if language == 'Lithuanian' :
		language = 'lt'
		return language
	if language == 'Malayalam' :
		language = 'ml'
		return language
	if language == 'Norwegian' :
		language = 'nb'
		return language
	if language == 'Persian' :
		language = 'fa'
		return language
	if language == 'Polish' :
		language = 'pl'
		return language
	if language == 'Portuguese' :
		language = 'pt'
		return language
	if language == 'Russian' :
		language = 'ru'
		return language
	if language == 'Spanish' :
		language = 'es'
		return language
	if language == 'Swedish' :
		language = 'sv'
		return language
	if language == 'Turkish' :
		language = 'tr'
		return language
	if language == 'Urdu' :
		language = 'ur'
		return language
	if language == 'Vietnamese' :
		language = 'vi'
		return language

def name(dispname):
	dispname=dispname.replace("&#39;","'")
	dispname=dispname.replace("\\","%")
	dispname=re.sub("(%x..)","", dispname)
	return dispname

def text(text):
	text = re.sub("(<.*?>)", "", text)
	text = text.replace("&#39;","'")
	text = text.replace("&nbsp;", " ")
	text = text.replace("&#10;", " ")
	text = text.replace('&quot;', '"')
	text = text.replace('&amp;', '&')
	text = text.replace('&lt;', '<')
	text = text.replace('&gt;', '>')
	return text

def searchstr(search_string):
	search_string = search_string.replace(' or ','%20OR%20')
	search_string = search_string.replace('#','%23')
	search_string = search_string.replace('@','%40')
	search_string = search_string.replace(' ','%20')
	return search_string

