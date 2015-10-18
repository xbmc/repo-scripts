import re, time

class TokenParser:
    tokens = {}
    tokenPrefix = '$'
    dataPrefix = '['
    dataPostfix = ']'
    dataSep = ','
    dataEscape = '\\'


    def parse(self,text):
        #print text
        text = re.sub('\\\\' + self.dataPostfix,'\a',text)
        text = re.sub('\\\\' + self.dataSep,'\b',text)
        for token in self.tokens:
            pattern = '{tpre}(?P<token>{token}){dpre}(?P<data>[^{dpost}]*){dpost}'.format(tpre=re.escape(self.tokenPrefix),token=token,dpre=re.escape(self.dataPrefix),dpost=re.escape(self.dataPostfix))
            text = re.sub(pattern,self.replacer,text)
        return text

    def replacer(self,m):
        data = m.group('data').split(self.dataSep)
        #print m.group(0)
        for x in range(len(data)):
            data[x] = data[x].replace('\a',self.dataPostfix)
            data[x] = data[x].replace('\b',self.dataSep)
        return self.tokenHandler(m.group('token'), data)

    def tokenHandler(self,token,data):
        return ''

class TitleTokenParser(TokenParser):
    def __init__(self,title,exif):
        self.title = title
        self.exif = exif

    def getEXIFTag(self,tag_name):
        if not self.exif: return ''
        t = self.exif.get('EXIF %s' % tag_name) or self.exif.get('Image %s' % tag_name)
        if not t: return ''
        t = t.values
        if not t: return ''
        return str(t)

    def error(self):
        import traceback
        traceback.print_exc()

    def tokenHandler(self,token,data):
        return self.tokens[token](self,*data)

    def processTITLE(self,*args):
        if not self.title: return ''
        title = self.title
        if not args: return title
        if args[0]:
            #ULTE
            mod = args[0].upper()
            if 'U' in mod: title = title.upper()
            if 'L' in mod: title = title.lower()
            if 'T' in mod: title = title.title()
            if 'S' in mod: title = title.replace('_',' ')
            if 'E' in mod:
                name_ext = title.rsplit('.',1)
                if len(name_ext) > 1 and len(name_ext[1]) > 2 and len(name_ext[1]) < 5: title = name_ext[0]

        if len(args) > 1: title = args[1] + title
        if len(args) > 2: title += args[2]
        return title

    def processDATETIME(self,*args):
        dt = self.getEXIFTag('DateTimeOriginal')
        if not dt: return ''
        if not args: return dt
        try:
            if args[0]: dt = time.strftime(args[0],time.strptime(dt,'%Y:%m:%d %H:%M:%S'))
        except:
            self.error()

        if len(args) > 1: dt = args[1] + dt
        if len(args) > 2: dt += args[2]
        return dt

    def processEXIF(self,*args):
        if not self.exif: return ''
        if not args: return ''
        data = self.getEXIFTag(args[0])
        if not data: return ''
        if len(args) > 1: data = args[1] + data
        if len(args) > 2: data += args[2]
        return data

    tokens = {'TITLE':processTITLE,'DATETIME':processDATETIME,'EXIF':processEXIF}
