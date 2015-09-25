#!/usr/bin/env python
# encoding: utf-8
# https://github.com/kroo/mobi-python
"""
Mobi.py

Created by Elliot Kroo on 2009-12-25.
Copyright (c) 2009 Elliot Kroo. All rights reserved.
"""

import sys
from struct import *
from lz77 import uncompress_lz77

class Mobi:
  def parse(self):
    """ reads in the file, then parses record tables"""
    self.contents = self.f.read()
    self.header = self.parseHeader()
    self.records = self.parseRecordInfoList()
    self.config = self.populate_config()

  def readRecord(self, recordnum, disable_compression=False):
    compressionType = self.config['palmdoc']['Compression']

    try:
      start = self.records[recordnum]['record Data Offset']

      # @TODO offset by record is not always 1
      # the correct record offset can be determined by examining
      # `book.records`
      end = self.records[recordnum + 1]['record Data Offset']
    except KeyError, e:
      sys.stderr.write('Could not find key value: %s\n' % str(e))
      return

    # @TODO configuration not present should run configurator.
    if not self.config:
      return

    if (compressionType == 1 or disable_compression):
      return self.contents[start : end]

    elif (compressionType == 2):
      extra = self.config['mobi']['extra bytes']
      result = uncompress_lz77(self.contents[start : end - extra])
      return result
    else: 
      sys.stderr.write('Error: could not recognize compression type "%s".' \
        % str(compressionType))
      exit(1)

  def readImageRecord(self, imgnum):
    if self.config:
      recordnum = self.config['mobi']['First Image index'] + imgnum
      return self.readRecord(recordnum, disable_compression=True)

  def author(self):
    "Returns the author of the book"
    return self.config['exth']['records'][100]

  def title(self):
    "Returns the title of the book"
    return self.config['mobi']['Full Name']

###########################  Private API ###########################

  def __init__(self, filename):
    try:
      # not sure if explicit type checking is the best way to do this.
      if isinstance(filename, str):
        self.f = open(filename, "rb")
      else:
        self.f = filename
    except IOError, e:
      sys.stderr.write("Could not open %s! " % filename)
      raise e
    self.offset = 0

  def __iter__(self):
    # @TODO configuration not present should run configurator.
    if not self.config: 
      return

    for record in range(1, self.config['mobi']['First Non-book index'] - 1):
      yield self.readRecord(record)

  def parseRecordInfoList(self):
    records = {}

    # read in all records in info list
    for recordID in range(self.header['number of records']):
      fields = [
        "record Data Offset",
        "UniqueID"
      ]

      headerfmt = '>II'
      headerlen = calcsize(headerfmt)
      infolist = self.contents[self.offset : self.offset + headerlen]

      # create tuple with info
      results = dict(zip(fields, unpack(headerfmt, infolist)))

      # increment offset into file
      self.offset += headerlen

      # futz around with the unique ID record, as the uniqueID's top 8 bytes 
      # are really the "record attributes":
      results['record Attributes'] = \
        (results['UniqueID'] & 0xFF000000) >> 24

      results['UniqueID'] = results['UniqueID'] & 0x00FFFFFF

      # store into the records dict
      records[results['UniqueID']] = results

    return records

  def parseHeader(self):
    fields = [
      "name",
      "attributes",
      "version",
      "created",
      "modified",
      "backup",
      "modnum",
      "appInfoId",
      "sortInfoID",
      "type",
      "creator",
      "uniqueIDseed",
      "nextRecordListID",
      "number of records"
    ]

    headerfmt = '>32shhIIIIII4s4sIIH'
    headerlen = calcsize(headerfmt)
    header = self.contents[self.offset : self.offset + headerlen]

    # unpack header, zip up into list of tuples
    results = dict(zip(fields, unpack(headerfmt, header)))

    # increment offset into file
    self.offset += headerlen

    return results

  # this function will populate the self.config attribute
  def populate_config(self):
    palmdocHeader = self.parsePalmDOCHeader()
    MobiHeader = self.parseMobiHeader()
    exthHeader = None
    if (MobiHeader['Has EXTH Header']):
      exthHeader = self.parseEXTHHeader()

    config = {
      'palmdoc': palmdocHeader,
      'mobi' : MobiHeader,
      'exth' : exthHeader
    }

    return config

  def parseEXTHHeader(self):
    headerfmt = '>III'
    headerlen = calcsize(headerfmt)

    header = self.contents[self.offset:self.offset + headerlen]

    fields = [
      'identifier',
      'header length',
      'record Count'
    ]

    # unpack header, zip up into list of tuples
    results = dict(zip(fields, unpack(headerfmt, header)))

    self.offset += headerlen

    results['records'] = {}

    for record in range(results['record Count']):

      recordType, recordLen = \
        unpack(">II", self.contents[self.offset : self.offset + 8])
      
      recordData = \
        self.contents[self.offset + 8 : self.offset+recordLen]

      results['records'][recordType] = recordData
      self.offset += recordLen

    return results

  def parseMobiHeader(self):
    headerfmt = '> IIII II 40s III IIIII IIII I 36s IIII 8s HHIIIII'
    headerlen = calcsize(headerfmt)

    fields = [
      "identifier",
      "header length",
      "Mobi type",
      "text Encoding",

      "Unique-ID",
      "Generator version",

      "-Reserved",

      "First Non-book index",
      "Full Name Offset",
      "Full Name Length",

      "Language",
      "Input Language",
      "Output Language",
      "Format version",
      "First Image index",

      "First Huff Record",
      "Huff Record Count",
      "First DATP Record",
      "DATP Record Count",

      "EXTH flags",

      "-36 unknown bytes, if Mobi is long enough",

      "DRM Offset",
      "DRM Count",
      "DRM Size",
      "DRM Flags",

      "-Usually Zeros, unknown 8 bytes",

      "-Unknown",
      "Last Image Record",
      "-Unknown",
      "FCIS record",
      "-Unknown",
      "FLIS record",
      "Unknown"
    ]

    header = self.contents[self.offset:self.offset+headerlen]

    # unpack header, zip up into list of tuples
    results = dict(zip(fields, unpack(headerfmt, header)))

    results['Start Offset'] = self.offset

    results['Full Name'] = (self.contents[
      self.records[0]['record Data Offset'] + results['Full Name Offset'] :
      self.records[0]['record Data Offset'] + \
        results['Full Name Offset'] + results['Full Name Length']])

    results['Has DRM'] = results['DRM Offset'] != 0xFFFFFFFF

    results['Has EXTH Header'] = (results['EXTH flags'] & 0x40) != 0

    self.offset += results['header length']

    def onebits(x, width=16):
      # Remove reliance on xrange()?
      return len(filter(lambda x: x == "1", 
        (str((x>>i)&1) for i in xrange(width - 1, -1, -1))))

    results['extra bytes'] = \
      2 * onebits(
        unpack(">H", self.contents[self.offset - 2 : self.offset])[0] & 0xFFFE)

    return results

  def parsePalmDOCHeader(self):
    headerfmt = '>HHIHHHH'
    headerlen = calcsize(headerfmt)

    fields = [
      "Compression",
      "Unused",
      "text length",
      "record count",
      "record size",
      "Encryption Type",
      "Unknown"
    ]

    offset = self.records[0]['record Data Offset']

    header = self.contents[offset:offset+headerlen]
    results = dict(zip(fields, unpack(headerfmt, header)))

    self.offset = offset+headerlen
    return results
