import dns.resolver

class ServiceRecord():
	_port = "61613"
	_url = "127.0.0.1"
	
	def __init__(self, url, port):
		self._port = port
		self._url = url
		

class ServiceLookUp():

	def __init__(self):
		self._resolver = dns.resolver.get_default_resolver()
		

	def lookUp(self,url):
	
		radioDNSData = self.get_cname( url )
		return self.get_services('_radiovis._tcp',radioDNSData, 'test')

	def get_cname(self, host):
		cname = None

		try:
			ans = self._resolver.query(host, 'CNAME')

			if len(ans.rrset.items) == 1:
				# Remove last (blank) field from host name.
				labels = ans[0].target.labels[0:-1]
				cname = '.'.join(labels)

		except dns.resolver.NoAnswer, e:
			return "No answer"
		except dns.resolver.NXDOMAIN, e:
			pass
		except dns.exception.DNSException, e:
			return "Exception: " + str(type(e))

		return cname

	def get_services(self, srv_record, host_name, service_name):
		"""
		Return a list of ServiceRecord objects for the DNS SRV records on the
		given host.
		"""
		ans = None

		# Form service record query: _radiovis._tcp at example.com
		# becomes _radiovis._tcp.example.com
		query = '.'.join([srv_record, host_name])

		try:
			ans = self._resolver.query(query, 'SRV')

		except dns.resolver.NoAnswer, e:
			return "No answer"
		except dns.resolver.NXDOMAIN, e:
			pass
		except dns.exception.DNSException, e:
			return "Exception: " + str(type(e))

		services = []

		if ans is not None and len(ans) > 0:
			for record in ans:
				# Remove last (blank) field from hostname then create
				# hostname string by joining with ".".
				target = record.target.labels[0:-1]
				target = ".".join(target)


				service_record = ServiceRecord(target,record.port)
				services.append(service_record)


		return services