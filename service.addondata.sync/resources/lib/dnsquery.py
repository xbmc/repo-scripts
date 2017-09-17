import socket


class DnsQuery:
    TypeA = 1
    # TypeAAAA = 28
    TypeCNAME = 5
    # TypeMX = 15
    TypeTXT = 16
    # TypeAll = 255

    def __init__(self, server):
        self.__server = server

    @staticmethod
    def get_host(url):
        start = url.index("//")
        start += 2
        end = url.find("/", start)
        if end > 0:
            return url[start:end]
        else:
            return url[start:]

    def resolve_dns(self, address, dns_types=(TypeA, TypeCNAME, TypeTXT)):
        sock = socket.socket(type=socket.SOCK_DGRAM)
        results = []
        for dns_type in dns_types:
            q = self.__create_request(address, dns_type)
            sock.settimeout(10.0)
            sock.sendto(q, (self.__server, 53))
            response = sock.recvfrom(1024)
            results += self.__parse_response(response[0])
        return results

    @staticmethod
    def __create_request(address, dns_type):
        # noinspection PyListCreation
        q = []
        q.append("\x00\x01")  # sequence
        q.append("\x01\x00")  # standard request
        q.append("\x00\x01")  # questions
        q.append("\x00\x00")  # answer RRS
        q.append("\x00\x00")  # authority RRS
        q.append("\x00\x00")  # additional RRS

        address_parts = address.split(".")
        for part in address_parts:
            q.append(chr(len(part)))
            q.append(part)
        q.append("\x00")
        q.append("\x00%s" % (chr(dns_type), ))
        q.append("\x00\x01")  # Class: IN
        return "".join(q)

    # noinspection PyUnusedLocal
    @staticmethod
    def __parse_response(response):
        results = []
        reader = DnsQuery.__ByteStringReader(response)
        transaction_id = reader.read_integer()
        flags = reader.read_integer()
        questions = reader.read_integer()
        answers = reader.read_integer()
        authority = reader.read_integer()
        additional = reader.read_integer()
        while True:
            length = reader.read_integer(1)
            if length == 0:
                break
            address_part = reader.read_string(length)
            # print address_part
            continue
        dns_type = reader.read_integer()
        direction = reader.read_integer()

        for i in range(0, answers):
            name = reader.read_full_string()
            # print "Name: %s" % (name,)

            answer_type = reader.read_integer()
            direction = reader.read_integer()
            ttl = reader.read_integer(4)
            length = reader.read_integer()
            address = []
            if answer_type == DnsQuery.TypeA:
                for int_value in range(0, length):
                    address.append(str(reader.read_integer(1)))
                address = ".".join(address)
            elif answer_type == DnsQuery.TypeCNAME:
                address = reader.read_full_string()
            # elif answer_type == answer_type == DnsQuery.TypeMX:
            #     address = reader.read_string(length)
            elif answer_type == DnsQuery.TypeTXT:
                length = reader.read_integer(1)
                address = reader.read_string(length)
            else:
                raise Exception("wrong type: %s" % (answer_type, ))

            # print ip
            results.append((answer_type, address))
        return results

    class __ByteStringReader:
        def __init__(self, byte_string):
            self.__byteString = byte_string
            self.__pointer = 0
            self.__resumePoint = 0
            # print "Input: %r" % (byteString, )

        def read_integer(self, length=2):
            val = self.read_string(length)
            val = self.__byte_to_int(val)
            # print val
            return val

        def read_full_string(self):
            value = ""
            while True:
                length = self.read_integer(1)
                if length == 0:
                    break
                elif length == 192:  # \xC0
                    # pointer found
                    new_pointer = self.read_integer(1)
                    old_pointer = self.__pointer
                    self.__pointer = new_pointer
                    value += self.read_full_string()
                    self.__pointer = old_pointer
                    break
                value += self.read_string(length)
                value += "."
                continue
            return value.strip('.')

        def read_string(self, length):
            # print "from: %s to %s" % (self.__pointer, self.__pointer + length)
            val = self.__byteString[self.__pointer:self.__pointer + length]
            # print "Value %r" % (val, )
            self.__pointer += length
            return val

        @staticmethod
        def __byte_to_int(byte_string):
            return int(byte_string.encode('hex'), 16)
