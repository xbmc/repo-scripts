import xbmc
'''DON'T USE IT ON ANDROID SYSTEM!!!'''
def reverse_noandroid(admin, input):
	returned = {v: k for k, v in input.items()} #Python 2.7
	#id_T2 = {k:v for (k,v) in d.items() if filter_string in k} #Python 3.0
	return returned