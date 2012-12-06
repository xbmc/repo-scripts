""" Tagger ID3 Constants """

__author__ = "Alastair Tse <alastair@tse.id.au>"
__license__ = "BSD"
__copyright__ = "Copyright (c) 2004, Alastair Tse" 

__revision__ = "$Id: constants.py,v 1.3 2004/12/21 12:02:06 acnt2 Exp $"

ID3_FILE_READ = 0
ID3_FILE_MODIFY = 1
ID3_FILE_NEW = 2

ID3V2_FILE_HEADER_LENGTH = 10
ID3V2_FILE_EXTHEADER_LENGTH = 5
ID3V2_FILE_FOOTER_LENGTH = 10
ID3V2_FILE_DEFAULT_PADDING = 512

ID3V2_DEFAULT_VERSION = 2.4

ID3V2_FIELD_ENC_ISO8859_1 = 0
ID3V2_FIELD_ENC_UTF16 = 1
ID3V2_FIELD_ENC_UTF16BE = 2
ID3V2_FIELD_ENC_UTF8 = 3





# ID3v2 2.2 Variables

ID3V2_2_FRAME_HEADER_LENGTH = 6

ID3V2_2_TAG_HEADER_FLAGS = [('compression', 6),
							('unsync', 7)]

ID3V2_2_FRAME_SUPPORTED_IDS = {
	'UFI':('bin','Unique File Identifier'), # FIXME
	'BUF':('bin','Recommended buffer size'), # FIXME
	'CNT':('pcnt','Play counter'),
	'COM':('comm','Comments'),
	'CRA':('bin','Audio Encryption'), # FIXME
	'CRM':('bin','Encrypted meta frame'), # FIXME
	'EQU':('bin','Equalisation'), # FIXME
	'ETC':('bin','Event timing codes'),
	'GEO':('geob','General Encapsulated Object'),
	'IPL':('bin','Involved People List'), # null term list FIXME
	'LNK':('bin','Linked Information'), # FIXME
	'MCI':('bin','Music CD Identifier'), # FIXME
	'MLL':('bin','MPEG Location Lookup Table'), # FIXME
	'PIC':('apic','Attached Picture'),
	'POP':('bin','Popularimeter'), # FIXME
	'REV':('bin','Reverb'), # FIXME
	'RVA':('bin','Relative volume adjustment'), # FIXME
	'STC':('bin','Synced Tempo Codes'), # FIXME
	'SLT':('bin','Synced Lyrics/Text'), # FIXME
	'TAL':('text','Album/Movie/Show'),
	'TBP':('text','Beats per Minute'),
	'TCM':('text','Composer'),
	'TCO':('text','Content Type'),
	'TCR':('text','Copyright message'),
	'TDA':('text','Date'),
	'TDY':('text','Playlist delay (ms)'),
	'TEN':('text','Encoded by'),
	'TIM':('text','Time'),
	'TKE':('text','Initial key'),
	'TLA':('text','Language(s)'),
	'TLE':('text','Length'),
	'TMT':('text','Media Type'),
	'TP1':('text','Lead artist(s)/Lead performer(s)/Performing group'),
	'TP2':('text','Band/Orchestra/Accompaniment'),
	'TP3':('text','Conductor'),
	'TP4':('text','Interpreted, remixed by'),
	'TPA':('text','Part of a set'),		
	'TPB':('text','Publisher'),
	'TOA':('text','Original artist(s)/performer(s)'),
	'TOF':('text','Original Filename'),
	'TOL':('text','Original Lyricist(s)/text writer(s)'),
	'TOR':('text','Original Release Year'),
	'TOT':('text','Original album/Movie/Show title'),
	'TRC':('text','International Standard Recording Code (ISRC'),
	'TRD':('text','Recording dates'),
	'TRK':('text','Track number/Position in set'),
	'TSI':('text','Size'),
	'TSS':('text','Software/hardware and settings used for encoding'),
	'TT1':('text','Content Group Description'),
	'TT2':('text','Title/Songname/Content Description'),
	'TT3':('text','Subtitle/Description refinement'),
	'TXT':('text','Lyricist(s)/Text Writer(s)'),
	'TYE':('text','Year'),
	'TXX':('wxxx','User defined text information'),
	'ULT':('bin','Unsynced Lyrics/Text'),
	'WAF':('url','Official audio file webpage'),
	'WAR':('url','Official artist/performer webpage'),
	'WAS':('url','Official audio source webpage'),
	'WCM':('url','Commercial information'),
	'WCP':('url','Copyright/Legal Information'),
	'WPM':('url','Official Publisher webpage'),
	'WXX':('wxxx','User defined URL link frame')
	}


ID3V2_2_FRAME_IMAGE_FORMAT_TO_MIME_TYPE = {
    'JPG':'image/jpeg',
    'PNG':'image/png',
    'GIF':'image/gif'
}

ID3V2_2_FRAME_MIME_TYPE_TO_IMAGE_FORMAT = {
    'image/jpeg':'JPG',
    'image/png':'PNG',
    'image/gif':'GIF'
}

# ID3v2 2.3 and above support

ID3V2_3_TAG_HEADER_FLAGS = [("ext", 6),
							("exp", 5),
							("footer", 4),
							("unsync", 7)]

ID3V2_3_FRAME_HEADER_LENGTH = 10
ID3V2_4_FRAME_HEADER_LENGTH = ID3V2_3_FRAME_HEADER_LENGTH

ID3V2_3_FRAME_TEXT_ID_TYPE = ['TIT1', 'TIT2', 'TIT3', 'TALB', 'TOAL', \
							  'TRCK', 'TPOS', 'TSST', 'TSRC']
ID3V2_3_FRAME_TEXT_PERSON_TYPE = ['TPE1', 'TPE2', 'TPE3', 'TPE4', 'TOPE', \
								  'TEXT', 'TOLY', 'TCOM', 'TMCL', 'TIPL', \
								  'TENC']
ID3V2_3_FRAME_TEXT_PROP_TYPE = ['TBPM', 'TLEN', 'TKEY', 'TLAN', 'TCON', \
								'TFLT', 'TMED']
ID3V2_3_FRAME_TEXT_RIGHTS_TYPE = ['TCOP', 'TPRO', 'TPUB', 'TOWN', 'TRSN', \
								  'TRSO']
ID3V2_3_FRAME_TEXT_OTHERS_TYPE = ['TOFN', 'TDLY', 'TDEN', 'TDOR', 'TDRC', \
								  'TDRL', 'TDTG', 'TSSE', 'TSOA', 'TSOP', \
								  'TSOT']
ID3V2_3_FRAME_IS_URL_TYPE = ['WCOM', 'WCOP', 'WOAF', 'WOAR', 'WOAS', \
							 'WORS', 'WPAY', 'WPUB']

ID3V2_3_FRAME_ONLY_FOR_2_3 = ['EQUA', 'IPLS', 'RVAD', 'TDAT', 'TIME', \
							  'TORY', 'TRDA', 'TSIZ', 'TYER']

ID3V2_4_FRAME_NEW_FOR_2_4 = ['ASPI', 'EQU2', 'RVA2', 'SEEK', 'SIGN', 'TDEN', \
							 'TDOR', 'TDRC', 'TDRL', 'TDTG', 'TIPL', 'TMCL', \
							 'TMOO', 'TPRO', 'TSOA', 'TSOP', 'TSOT', 'TSST']

ID3V2_3_FRAME_FLAGS = ['status', 'format', 'length', 'tagpreserve', \
					   'filepreserve', 'readonly', 'groupinfo', \
					   'compression', 'encryption', 'sync', 'datalength']

ID3V2_3_FRAME_STATUS_FLAGS = [('tagpreserve', 6),
							  ('filepreserve', 5),
							  ('readonly', 4)]

ID3V2_3_FRAME_FORMAT_FLAGS = [('groupinfo', 6),
							  ('compression', 3),
							  ('encryption', 2),
							  ('sync', 1),
							  ('datalength', 0)]

ID3V2_3_ABOVE_SUPPORTED_IDS = {
	'AENC':('bin','Audio Encryption'), # FIXME
	'APIC':('apic','Attached Picture'),
	'ASPI':('bin','Seek Point Index'), # FIXME		
	'COMM':('comm','Comments'),
	'COMR':('bin','Commerical Frame'), # FIXME
	'EQU2':('bin','Equalisation'), # FIXME		
	'ENCR':('bin','Encryption method registration'), # FIXME
	'ETCO':('bin','Event timing codes'), # FIXME
	'GEOB':('geob','General Encapsulated Object'),
	'GRID':('bin','Group ID Registration'), # FIXME
	'LINK':('link','Linked Information'), # FIXME
	'MCDI':('bin','Music CD Identifier'),
	'MLLT':('bin','Location lookup table'), # FIXME
	'OWNE':('bin','Ownership frame'), # FIXME
	'PCNT':('pcnt','Play Counter'),
	'PRIV':('bin','Private frame'), # FIXME
	'POPM':('bin','Popularimeter'), # FIXME
	'POSS':('bin','Position Synchronisation frame'), # FIXME
	'RBUF':('bin','Recommended buffer size'), # FIXME
	'RVA2':('bin','Relative volume adjustment'), #FIXME
	'RVRB':('bin','Reverb'), # FIXME
	'SIGN':('bin','Signature'), # FIXME
	'SEEK':('pcnt','Seek'),
	'SYTC':('bin','Synchronised tempo codes'), # FIXME
	'SYLT':('bin','Synchronised lyrics/text'), # FIXME
	'TALB':('text','Album/Movie/Show Title'),
	'TBPM':('text','BPM'),
	'TCOM':('text','Composer'),		
	'TCON':('text','Content type'),		
	'TCOP':('text','Copyright'),
	'TDEN':('text','Encoding time'),
	'TDLY':('text','Playlist delay'),
	'TDOR':('text','Original release time'),
	'TDRC':('text','Recording time'),
	'TDRL':('text','Release time'),
	'TDTG':('text','Tagging time'),
	'TENC':('text','Encoded by'),		
	'TEXT':('text','Lyricist/Text writer'),
	'TFLT':('text','File type'),
	'TIPL':('text','Musicians credits list'),
	'TIT1':('text','Content group description'),
	'TIT2':('text','Title/Songname/Content Description'),
	'TIT3':('text','Subtitle/Description refinement'),
	'TKEY':('text','Initial Key'),
	'TLAN':('text','Language'),
	'TLEN':('text','Length'),
	'TMCL':('text','Musician credits list'),
	'TMED':('text','Media type'),
	'TOAL':('text','Original album/movie/show title'),
	'TOFN':('text','Original Filename'),
	'TOPE':('text','Original artist/performer'),
	'TOLY':('text','Original lyricist/text writer'),
	'TOWN':('text','File owner/licensee'),
	'TPE1':('text','Lead Performer(s)/Soloist(s)'),
	'TPE2':('text','Band/Orchestra Accompaniment'),
	'TPE3':('text','Conductor'),
	'TPE4':('text','Interpreted, remixed by'),
	'TPOS':('text','Part of a set'), # [0-9/]
	'TPUB':('text','Publisher'),
	'TRCK':('text','Track'), # [0-9/]
	'TRSN':('text','Internet radio station name'),
	'TRSO':('text','Internet radio station owner'),
	'TSOA':('text','Album sort order'),
	'TSOP':('text','Performer sort order'),
	'TSOT':('text','Title sort order'),
	'TSSE':('text','Software/Hardware and settings used for encoding'),
	'TSST':('text','Set subtitle'),
	'TSRC':('text','International Standard Recording Code (ISRC)'), # 12 chars
	'TXXX':('wxxx','User defined text'),
	'UFID':('bin','Unique File Identifier'), # FIXME
	'USER':('bin','Terms of use frame'), # FIXME (similar to comment)
	'USLT':('comm','Unsynchronised lyris/text transcription'),
	'WCOM':('url','Commercial Information URL'),
	'WCOP':('url','Copyright/Legal Information'),
	'WOAF':('url','Official audio file webpage'),		
	'WOAR':('url','Official artist performance webpage'),
	'WOAS':('url','Official audio source webpage'),
	'WORS':('url','Official internet radio station homepage'),
	'WPAY':('url','Payment URL'),
	'WPUB':('url','Official publisher webpage'),
	'WXXX':('wxxx','User defined URL link frame'),
	# ID3v2.3 only tags
	'EQUA':('bin','Equalization'),
	'IPLS':('bin','Invovled people list'),
	'RVAD':('bin','Relative volume adjustment'),
	'TDAT':('text','Date'),
	'TIME':('text','Time'),
	'TORY':('text','Original Release Year'),
	'TRDA':('text','Recording date'),
	'TSIZ':('text','Size'),
	'TYER':('text','Year')		
}

ID3V2_3_APIC_PICT_TYPES = {
    0x00: 'Other',
    0x01: '32x32 PNG Icon',
    0x02: 'Other Icon',
    0x03: 'Cover (Front)',
    0x04: 'Cover (Back)',
    0x05: 'Leaflet Page',
    0x06: 'Media',
    0x07: 'Lead Artist/Lead Performer/Soloist',
    0x08: 'Artist/Performer',
    0x09: 'Conductor',
    0x0a: 'Band/Orchestra',
    0x0b: 'Composer',
    0x0c: 'Lyricist/text writer',
    0x0d: 'Recording Location',
    0x0e: 'During Recording',
    0x0f: 'During Performance',
    0x10: 'Movie/Video Screen Capture',
    0x11: 'A bright coloured fish',
    0x12: 'Illustration',
    0x13: 'Band/artist logotype',
    0x14: 'Publisher/Studio logotype'
}    

