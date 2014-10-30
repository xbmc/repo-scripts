# -*- coding: utf-8 -*-

import codecs
import sys
import os


class Lat2Cyr:

    lat_to_cyr = {
        # Big letters
        u'A': u'А', u'S': u'С', u'D': u'Д', u'F': u'Ф', u'G': u'Г',
        u'H': u'Х', u'J': u'Ј', u'K': u'К', u'L': u'Л', u'Č': u'Ч',
        u'Ć': u'Ћ', u'Ž': u'Ж', u'Lj': u'Љ', u'Nj': u'Њ', u'E': u'Е',
        u'R': u'Р', u'T': u'Т', u'Z': u'З', u'U': u'У', u'I': u'И',
        u'O': u'О', u'P': u'П', u'Š': u'Ш', u'Đ': u'Ђ', u'Dž': u'Џ',
        u'C': u'Ц', u'V': u'В', u'B': u'Б', u'N': u'Н', u'M': u'М',
        u'Dz': u'Ѕ',
        # small letters
        u'a': u'а', u's': u'с', u'd': u'д', u'f': u'ф', u'g': u'г',
        u'h': u'х', u'j': u'ј', u'k': u'к', u'l': u'л', u'č': u'ч',
        u'ć': u'ћ', u'ž': u'ж', u'lj': u'љ', u'nj': u'њ', u'e': u'е',
        u'r': u'р', u't': u'т', u'z': u'з', u'u': u'у', u'i': u'и',
        u'o': u'о', u'p': u'п', u'š': u'ш', u'đ': u'ђ', u'dž': u'џ',
        u'c': u'ц', u'v': u'в', u'b': u'б', u'n': u'н', u'm': u'м',
        u'dz': u'ѕ'
    }

    cyr_to_lat = {
        # Big letters
        u'А': u'A', u'С': u'S', u'Д': u'D', u'Ф': u'F', u'Г': u'G',
        u'Х': u'H', u'Ј': u'J', u'К': u'K', u'Л': u'L', u'Ч': u'Č',
        u'Ћ': u'Ć', u'Ж': u'Ž', u'Љ': u'Lj', u'Њ': u'Nj', u'Е': u'E',
        u'Р': u'R', u'Т': u'T', u'З': u'Z', u'У': u'U', u'И': u'I',
        u'О': u'O', u'П': u'P', u'Ш': u'Š', u'Ђ': u'Đ', u'Џ': u'Dž',
        u'Ц': u'C', u'В': u'V', u'Б': u'B', u'Н': u'N', u'М': u'M',
        u'Ѕ': u'Dz',
        # small letters
        u'а': u'a', u'с': u's', u'д': u'd', u'ф': u'f', u'г': u'g',
        u'х': u'h', u'ј': u'j', u'к': u'k', u'л': u'l', u'ч': u'č',
        u'ћ': u'ć', u'ж': u'ž', u'љ': u'lj', u'њ': u'nj', u'е': u'e',
        u'р': u'r', u'т': u't', u'з': u'z', u'у': u'u', u'и': u'i',
        u'о': u'o', u'п': u'p', u'ш': u'š', u'ђ': u'đ', u'џ': u'dž',
        u'ц': u'c', u'в': u'v', u'б': u'b', u'н': u'n', u'м': u'm',
        u'ѕ': u'dz'
    }

    two_letters_fix = {
        # Big letters
        u'Lj': u'Љ', u'LJ': u'Љ', u'Nj': u'Њ', u'NJ': u'Њ', u'Dž': u'Џ',
        u'DŽ': u'Џ', u'Dz': u'Ѕ', u'DZ': u'Ѕ',
        # small letters
        u'lj': u'љ', u'nj': u'њ', u'dž': u'џ', u'dz': u'ѕ'
    }

    def lat2cyr(self, txt, encoding='cp1250'):
        if not txt:
            return txt
        if not isinstance(txt, unicode):
            # print 'Decoding'
            lat = txt.decode(encoding)  # copy & force unicode
        else:
            lat = txt[:]  # copy
        # First replace two letters to one letter
        for c, l in self.two_letters_fix.items():
            lat = lat.replace(c, l)
        # Now replace all latin to cyrillic letters
        for c, l in self.lat_to_cyr.items():
            lat = lat.replace(c, l)
        # Fix for <i>, <b> and other letters between < >
        for c, l in self.cyr_to_lat.items():
            lat = lat.replace('<'+c+'>', '<'+l+'>')
            lat = lat.replace('</'+c+'>', '</'+l+'>')
        return lat

    # Call this funciton to convert latin file to cyrillic
    def convert2cyrillic(self, fileIn, encoding=None):
        if os.path.isfile(fileIn):
            if not encoding:
                # print 'Detecting encoding'
                encoding = self.getEncoding(fileIn)
                # print 'Found encoding type: %s\n' % encoding
            extension = (os.path.splitext(fileIn)[1])
            ime = (os.path.splitext(fileIn)[0])
            fileIn = codecs.open(fileIn, 'r', encoding)
            fileInLines = fileIn.readlines()
            fileIn.close()
            fileOutName = ime + '.cyr' + extension
            fileOut = codecs.open(fileOutName, 'w', 'utf8')

            i = 1
            for line in fileInLines:
                out = self.lat2cyr(line)
                fileOut.write(out)
                i += 1
            fileOut.close()
            return fileOutName
        else:
            return False

    def detectEncoding(self, string):
        encodinsList = ['utf8', 'cp1250']
        errors = 'strict'
        if isinstance(string, unicode):
            return 'unicode'
        else:
            for enc in encodinsList:
                try:
                    string = string.decode(enc, errors)
                    return enc
                except UnicodeError:
                    continue
            raise UnicodeError('Failed to convert %r' % string)

    def getEncoding(self, filename):
        f = open(filename, 'r')
        lines = f.readlines()
        f.close()
        enc_tryouts = []
        encoding = ''
        for line in lines:
            enc_tryouts.append(self.detectEncoding(line))
        for enc in enc_tryouts:
            if enc == 'utf8' and (encoding == '' or encoding == 'utf8'):
                encoding = 'utf8'
            else:
                if enc != 'utf8':
                    encoding = enc
        return encoding
