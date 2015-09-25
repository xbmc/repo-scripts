from struct import unpack, pack, calcsize
from mobi_languages import LANGUAGES
from lz77 import uncompress

def LOG(*args):
    pass

MOBI_HDR_FIELDS = (
    ("id", 16, "4s"),
    ("header_len", 20, "I"),
    ("mobi_type", 24, "I"),
    ("encoding", 28, "I"),
    ("UID", 32, "I"),
    ("generator_version", 36, "I"),
    ("reserved", 40, "40s"),
    ("first_nonbook_idx", 80, "I"),
    ("full_name_offs", 84, "I"),
    ("full_name_len", 88, "I"),
    ("locale_highbytes", 92, "H"),
    ("locale_country", 94, "B"),
    ("locale_language", 95, "B"),
    ("input_lang", 96, "I"),
    ("output_lang", 100, "I"),
    ("format_version", 104, "I"),
    ("first_image_idx", 108, "I"),
    ("huff/cdic_record", 112, "I"),
    ("huff/cdic_count", 116, "I"),
    ("datp_record", 120, "I"),
    ("datp_count", 124, "I"),
    ("exth_flags", 128, "I"),
    ("unknowni@132", 132, "32s"),
    ("unknown@164", 164, "I"),
    ("drm_offs", 168, "I"),
    ("drm_count", 172, "I"),
    ("drm_size", 176, "I"),
    ("drm_flags", 180, "I"),
    ("unknown@184", 184, "I"),
    ("unknown@188", 188, "I"),
    ("unknown@192", 192, "H"),
    ("last_image_record", 194, "H"),
    ("unknown@196", 196, "I"),
    ("fcis_record", 200, "I"),
    ("unknown@204", 204, "I"),
    ("flis_record", 208, "I"),
    ("unknown@212", 212, "I"),
    ("extra_data_flags", 242, "H")
    )

EXTH_FMT = ">4x2I"
'''4x = "EXTH", I = hlen, I = record count'''

EXTH_RECORD_TYPES = {
        1: 'drm server id',
        2: 'drm commerce id',
        3: 'drm ebookbase book id',
        100: 'author',  # list
        101: 'publisher',  # list
        102: 'imprint',
        103: 'description',
        104: 'isbn',  # list
        105: 'subject',  # list
        106: 'publication date',
        107: 'review',
        108: 'contributor',  # list
        109: 'rights',
        110: 'subjectcode',  # list
        111: 'type',
        112: 'source',
        113: 'asin',
        114: 'version number',  # int
        115: 'sample',  # int (or bool)?
        116: 'start reading',
        117: 'adult',
        118: 'retail price',
        119: 'retail price currency',
        201: 'cover offset',  # int
        202: 'thumbnail offset',  # int
        203: 'has fake cover',  # bool?
        208: 'watermark',
        209: 'tamper proof keys',
        401: 'clipping limit',  # int
        402: 'publisher limit',
        404: 'ttsflag',
        501: 'cde type',
        502: 'last update time',
        503: 'updated title'
        }

PRC_HDRFMT = '>H2xIHHI'  # Compression,unused,Len,Count,Size,Pos


def parse_palmdb(filename):
    import palm
    db = palm.Database(filename)
    return db


class Book:
    def __init__(self, fn):
        self.filename = fn

         # Set some fields to defaults
        self.title = fn
        self.author = "??"
        self.language = "??"
        self.is_a_book = False

        f = open(fn)
        d = f.read(68)
        f.close()
        encodings = {
                1252: 'cp1252',
                65001: 'utf-8'
                }
        supported_types = ('BOOKMOBI', 'TEXtREAd')
        self.type = d[60:68]

        if self.type not in supported_types:
            LOG(1, "Unsupported file type %s" % (self.type))
            return None

        try:
            db = parse_palmdb(fn)
        except:
            return None

        self.is_a_book = True
         # now we have a better guess at the title, use it for now
        self.title = db.name

        self.records = db.records
        rec0 = self.records[0].data
        #LOG(5,repr(rec0))
        if self.type == 'BOOKMOBI':
            LOG(3, "This is a MOBI book")
            self.mobi = {}
            for field, pos, fmt in MOBI_HDR_FIELDS:
                end = pos + calcsize(fmt)
                if (end > len(rec0) or
                    ("header_len" in self.mobi
                        and end > self.mobi["header_len"])):
                        continue
                LOG(4, "field: %s, fmt: %s, @ [%d:%d], data: %s" % (
                    field, fmt, pos, end, repr(rec0[pos:end])))
                (self.mobi[field], ) = unpack(">%s" % fmt, rec0[pos:end])

            LOG(3, "self.mobi: %s" % repr(self.mobi))

             # Get and decode the book name
            if self.mobi['locale_language'] in LANGUAGES:
                lang = LANGUAGES[self.mobi['locale_language']]
                if self.mobi['locale_country'] == 0:
                    LOG(2, "Book language: %s" % lang[0][1])
                    self.language = "%s (%s)" % (lang[0][1], lang[0][0])
                elif self.mobi['locale_country'] in lang:
                    country = lang[self.mobi['locale_country']]
                    LOG(2, "Book language is %s (%s)" % (
                        lang[0][1], country[1]))
                    self.language = "%s (%s-%s)" % (
                        lang[0][1],
                        lang[0][0],
                        country[0]
                        )

            pos = self.mobi['full_name_offs']
            end = pos + self.mobi['full_name_len']
            self.title = rec0[pos:end].decode(encodings[self.mobi['encoding']])

            LOG(2, "Book name: %s" % self.title)

            if self.mobi['id'] != 'MOBI':
                LOG(0, "Mobi header missing!")
                return None

            if (0x40 & self.mobi['exth_flags']):  # check for EXTH
                self.exth = parse_exth(rec0, self.mobi['header_len'] + 16)
                LOG(3, "EXTH header: %s" % repr(self.exth))
                if 'author' in self.exth:
                    self.author = ' & '.join(self.exth['author'])
                else:
                    self.author = "n/a"
                self.rawdata = d

                if (('updated title' in self.exth) and
                    (type(self.exth['updated title']) is str)):
                    self.title = ' '.join(self.exth['updated title'])

        elif self.type == 'TEXtREAd':
            LOG(2, "This is an older MOBI book")
            self.rawdata = d
            compression, data_len, rec_count, rec_size, pos = unpack(
                    PRC_HDRFMT, rec0[:calcsize(PRC_HDRFMT)])
            LOG(3, "compression %d, data_len %d, rec_count %d, rec_size %d" %
                    (compression, data_len, rec_count, rec_size))
            if compression == 2:
                data = uncompress(self.records[1].data)
            else:
                data = self.records[1].data
            from BeautifulSoup import BeautifulSoup
            soup = BeautifulSoup(data)

            self.metadata = soup.fetch("dc-metadata")
            try:
                self.title = soup.fetch("dc:title")[0].getText()
                self.author = soup.fetch("dc:creator")[0].getText()
                self.language = soup.fetch("dc:language")[0].getText()
            except:
                self.title, self.author, self.language = ("Unknown", "Unknown",
                        "en-us")

    def to_html(self):
        last_idx = (
            self.mobi['first_image_idx'] if 'mobi' in self.__dict__ else -1)
        return ''.join([uncompress(x.data) for x in self.records[1:last_idx]])


def parse_exth(data, pos):
    ret = {}
    n = 0
    if (pos != data.find('EXTH')):
        LOG(0, "EXTH header not found where it should be @%d" % pos)
        return None
    else:
        end = pos + calcsize(EXTH_FMT)
        (hlen, count) = unpack(EXTH_FMT, data[pos:end])
        LOG(4, "pos: %d, EXTH header len: %d, record count: %d" % (
            pos, hlen, count))
        pos = end
        while n < count:
            end = pos + calcsize(">2I")
            t, l = unpack(">2I", data[pos:end])
            v = data[end:pos + l]
            if l - 8 == 4:
                v = unpack(">I", v)[0]
            if t in EXTH_RECORD_TYPES:
                rec = EXTH_RECORD_TYPES[t]
                LOG(4, "EXTH record '%s' @%d+%d: '%s'" % (
                    rec, pos, l - 8, v))
                if rec not in ret:
                    ret[rec] = [v]
                else:
                    ret[rec].append(v)

            else:
                LOG(4, "Found an unknown EXTH record type %d @%d+%d: '%s'" %
                        (t, pos, l - 8, repr(v)))
            pos += l
            n += 1
    return ret
