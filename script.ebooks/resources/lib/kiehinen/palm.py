from struct import *

'''
32s - name
H - attributes
H - version
I - creation_date
I - modification_date
I - last_backup_date
I - modification_number
I - appInfoID
I - sortInfoID
4s - type
4s - creator
I - uniqueIDseec
I - nextRecordListID
H - number_of_records
'''

HDR_FMT = '>32sHHIIIIII4s4sIIH'
REC_FMT = '>IB3s'  # offset, attributes, info (actually 3 byte integer)


class Record():
    def __init__(self, **entries):
        self.__dict__.update(entries)


class Database():
    def __init__(self, filename):
        f = open(filename, 'rb')
        self.header = f.read(calcsize(HDR_FMT))
        (self.name, self.attributes, self.version, self.creation_date,
                self.modification_date, self.last_backup_date,
                self.modification_number, self.appInfoID, self.sortInfoID,
                self.type, self.creator, self.uniqueIDseed,
                self.nextRecordListID,
                self.number_of_rec_info) = unpack(HDR_FMT, self.header)
        recs = []
        self.records = []

        for i in range(self.number_of_rec_info):
            rec_info = unpack(REC_FMT, f.read(calcsize(REC_FMT)))
            offset = rec_info[0]
            flags = rec_info[1]
            (hi, lo) = unpack(">BH", rec_info[2])
            uid = hi * 2 ** 16 + lo
            recs.append((offset, flags, uid))

        recs.append((f.tell(), 0, 0))
        pos = f.tell()
        end = recs[0][0]
        self.garbage = f.read(end - pos)

        while len(recs) > 1:
            pos, flags, uid = recs.pop(0)
            if f.tell() != pos:
                print("ERROR %d != %d" % (f.tell(), pos))
                f.seek(pos)
            end = recs[0][0]
            l = end - pos
            data = f.read(l)
            self.records.append(Record(**{
                'data': data,
                'uid': uid,
                'flags': flags,
                'pos': pos
                }))
        f.close()
