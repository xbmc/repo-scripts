# main imports
import sys
import os

try:
    import xbmc
    DEBUG = False
except:
    DEBUG = True

import xbmcgui
import re
import time
from xbmcaddon import Addon

__Settings__ = Addon(id="weather.weatherplus")

class Main:
	def __init__(self, loc=1):
		base_url = "http://v.imwx.com/v/wxcom/"
		dialog = xbmcgui.Dialog()
		video_num = dialog.select("Which Video Slot Would You Change?", ["Video #1", "Video #2", "Video #3"])
		if ( video_num != -1 ):
			slot = video_num + 1
		else:
			#__Settings__.openSettings()
			return
		channel = dialog.select("Choose a Channel", ["Weather.com", "ABC", "CBS", "FOX", "NBC"])
		if ( channel == 0 ):
			category = dialog.select("Choose a Category", ["National", "Northeast", "South", "Midwest", "West", "Travel"])
			if ( category == 0 ):
				video = dialog.select("Select a Video You Want", ["A National Look at the Next 3 Days", "Latest forecast for severe weather", "Today's top forecasts", "Weekly Planner"])
				video_url = base_url + ("national.mov", "stormwatch.mov", "topstory.mov", "weekly.mov")[video]
				__Settings__.setSetting( ("video1", "video2", "video3")[slot], ("A National Look at the Next 3 Days", "Latest forecast for severe weather", "Today's top forecasts", "Weekly Planner")[video] )
				__Settings__.setSetting( ("video1_url", "video2_url", "video3_url")[slot], video_url )
			elif ( category == 1 ):
				video = dialog.select("Select a Video You Want", ["Northeast Regional Forecast", "Albany", "Baltimore", "Boston", "Buffalo", "Burlington", "Charleston", "Cincinnati", "Cleveland", "Columbus", "Harrisburg", "Hartford", "Johnstown", "New York", "Norfolk", "Philadephia", "Pittsburgh", "Providence", "Richmond", "Roanoke", "Rochester", "Syracuse", "Toledo", "Washington, DC", "Wilkes-Barre"])
				video_url = base_url + ("northeast", "albany", "baltimore", "boston", "buffalo", "burlington", "charleston", "cincinnati", "cleveland", "columbus", "harrisburg", "hartford", "johnstown", "newyorkcity", "norfolk", "philadephia", "pittsburgh", "providence", "richmond", "roanoke", "rochester", "syracuse", "toledo", "washingtondc", "wilkes-barre")[video] + ".mov"
				__Settings__.setSetting( ("video1", "video2", "video3")[slot], ("Northeast Regional Forecast", "Albany", "Baltimore", "Boston", "Buffalo", "Burlington", "Charleston", "Cincinnati", "Cleveland", "Columbus", "Harrisburg", "Hartford", "Johnstown", "New York", "Norfolk", "Philadephia", "Pittsburgh", "Providence", "Richmond", "Roanoke", "Rochester", "Syracuse", "Toledo", "Washington, DC", "Wilkes-Barre")[video] )
				__Settings__.setSetting( ("video1_url", "video2_url", "video3_url")[slot], video_url )
			elif ( category == 2 ):
				video = dialog.select("Select a Video You Want", ["Southeast Regional Forecast", "Atlanta", "Baton Rouge", "Birmingham", "Charlotte", "Chattanooga", "Columbia", "Ft. Myers", "Greensboro", "Greenville", "Huntsville", "Jackson", "Jacksonville", "Knoxville", "Memphis", "Miami", "Mobile", "Nashville", "New Orleans", "Orlando", "Raleigh", "Savannah", "Shreveport", "Tampa", "Tri-Cities", "West Palm Beach"])
				video_url = base_url + ("south", "atlanta", "batonrouge", "birmingham", "charlotte", "chattanooga", "columbia", "ftmyers", "greensboro", "greenville", "huntsville", "jackson", "jacksonville", "knoxville", "memphis", "miami", "mobile", "nashville", "neworleans", "orlando", "raleigh", "savannah", "shreveport", "tampa", "tricities", "westpalm")[video] + ".mov"
				__Settings__.setSetting( ("video1", "video2", "video3")[slot], ("Southeast Regional Forecast", "Atlanta", "Baton Rouge", "Birmingham", "Charlotte", "Chattanooga", "Columbia", "Ft. Myers", "Greensboro", "Greenville", "Huntsville", "Jackson", "Jacksonville", "Knoxville", "Memphis", "Miami", "Mobile", "Nashville", "New Orleans", "Orlando", "Raleigh", "Savannah", "Shreveport", "Tampa", "Tri-Cities", "West Palm Beach")[video] )
				__Settings__.setSetting( ("video1_url", "video2_url", "video3_url")[slot], video_url )
			elif ( category == 3 ):
				video = dialog.select("Select a Video You Want", ["Midwest Regional Forecast", "Cedar Rapids", "Champaign", "Chicago", "Davenport", "Dayton", "Des Moines", "Detroit", "Evansville", "Flint", "Grand Rapids", "Green Bay", "Indianapolis", "Kansas City", "Lexington", "Little Rock", "Louisville", "Madison", "Milwaukee", "Minneapolis", "Oklahoma City", "Omaha", "Paducah", "South Bend", "Springfield", "St. Louis", "Tulsa", "Wichita"])
				video_url = base_url + ("midwest", "cedarrapids", "champaign", "chicago", "davenport", "dayton", "desmoines", "detroit", "evansville", "flint", "grandrapids", "greenbay", "indianapolis", "kansascity", "lexington", "littlerock", "louisville", "madison", "milwaukee", "minneapolis", "okc", "omaha", "paducah", "southbend", "springfield", "stlouis", "tulsa", "wichita")[video] + ".mov"
				__Settings__.setSetting( ("video1", "video2", "video3")[slot], ("Midwest Regional Forecast", "Cedar Rapids", "Champaign", "Chicago", "Davenport", "Dayton", "Des Moines", "Detroit", "Evansville", "Flint", "Grand Rapids", "Green Bay", "Indianapolis", "Kansas City", "Lexington", "Little Rock", "Louisville", "Madison", "Milwaukee", "Minneapolis", "Oklahoma City", "Omaha", "Paducah", "South Bend", "Springfield", "St. Louis", "Tulsa", "Wichita")[video] )
				__Settings__.setSetting( ("video1_url", "video2_url", "video3_url")[slot], video_url )
			elif ( category == 4 ):
				video = dialog.select("Select a Video You Want", ["West Regional Forecast", "Albuquerque", "Austin", "Colorado Spring", "Dallas", "Denver", "El Paso", "Fresno", "Harlingen", "Honolulu", "Houston", "Las Vegas", "Los Angeles", "Phoenix", "Portland", "Sacramento", "Salt Lake City", "San Antonio", "San Diego", "San Francisco", "Seattle", "Spokane", "Tucson", "Waco"])
				video_url = base_url + ("west", "albuquerque", "austin", "coloradospring", "dallas", "denver", "elpaso", "fresno", "harlingen", "honolulu", "houston", "vegas", "losangeles", "phoenix", "portland", "sacramento", "saltlake", "sanantonio", "sandiego", "sanfrancisco", "seattle", "spokane", "tucson", "waco")[video] + ".mov"
				__Settings__.setSetting( ("video1", "video2", "video3")[slot], ("West Regional Forecast", "Albuquerque", "Austin", "Colorado Spring", "Dallas", "Denver", "El Paso", "Fresno", "Harlingen", "Honolulu", "Houston", "Las Vegas", "Los Angeles", "Phoenix", "Portland", "Sacramento", "Salt Lake City", "San Antonio", "San Diego", "San Francisco", "Seattle", "Spokane", "Tucson", "Waco")[video] )
				__Settings__.setSetting( ("video1_url", "video2_url", "video3_url")[slot], video_url )
			elif ( category == 5 ):
				video = dialog.select("Select a Video You Want", ["Driving Forecast", "Boat and Beach Forecast", "Mexico Vacation Forecast", "Hawaii Vacation Forecast", "Florida Vacation Forecast", "Alaska Vacation Forecast", "European Vaccation Forecast", "Bahamas Vacation Forecast", "Canada Vacation Forecast", "Caribbean Vacation Forecast"])
				video_url = base_url + ("driving", "boatandbeach", "mexico", "hawaii", "florida", "alaska", "europe", "bahamas", "canada", "caribbean")[video] + ".mov"
				__Settings__.setSetting( ("video1", "video2", "video3")[slot], ("Driving Forecast", "Boat and Beach Forecast", "Mexico Vacation Forecast", "Hawaii Vacation Forecast", "Florida Vacation Forecast", "Alaska Vacation Forecast", "European Vaccation Forecast", "Bahamas Vacation Forecast", "Canada Vacation Forecast", "Caribbean Vacation Forecast")[video] )
				__Settings__.setSetting( ("video1_url", "video2_url", "video3_url")[slot], video_url )
		# ABC
		elif ( channel == 1 ):
			video_list = [ 
				"ABC (Columbia, SC)", 
				"ABC 2 (Baton Rouge, LA)",
				"ABC 3 (Wilmington, NC)",
				"ABC 4 (Hawaii)",
				"ABC 5 (Cleveland, OH)",
				"ABC 5 (Oklahoma City, OK)",
				"ABC 6 (Philadephia, PA)", 
				"ABC 7 (Los Angeles, CA)", 
				"ABC 7 (San Francisco, CA)", 
				"ABC 7 (Denver, CO)",
				"ABC 7 (Chicago, IL)",
				"ABC 7 (Omaha, NE)",
				"ABC 7 (Buffalo, NY)", 
				"ABC 7 (New York, NY)",
				"ABC 8 (Grand Junction, CO)",
				"ABC 8 (CT)",
				"ABC 8 (Charleston, WV)",
				"ABC 9 (Orlando, FL)",
				"ABC 9 (Kansas City, MO)",
				"ABC 9 (NH)",
				"ABC 9 (Cincinnati, OH)",
				"ABC 11 (Louisville, KY)",
				"ABC 12 (Flint, MI)",
				"ABC 13 (Colorado Springs, CO)", 
				"ABC 13 (Asheville, NC)",
				"ABC 13 (Houston, TX)", 
				"ABC 13 (Norfolk, VA)", 
				"ABC 15 (AZ)", 
				"ABC 20 (Gainesville, FL)" ]
			video = dialog.select("Select a Video You Want", video_list)
			__Settings__.setSetting( "video%d" % slot, video_list[video] )
			__Settings__.setSetting( "video%d_url" % slot, "" )
		# CBS
		elif ( channel == 2 ):
			video_list = [
				"CBS (Boston, MA)",
				"CBS (Detroit, MI)",
				"CBS 2 (Los Angeles, CA)",
				"CBS 2 (Cedar Rapids, IA)",
				"CBS 2 (New York, NY)",
				"CBS 2 (Chicago, IL)",
				"CBS 2 (Pittsburgh, PA)",
				"CBS 3 (Philadelphia, PA)",
				"CBS 4 (Denver, CO)",
				"CBS 4 (Miami, FL)",
				"CBS 4 (Minneapolis, MN)",
				"CBS 5 (Grand Junction, CO)",
				"CBS 8 (Montgomery, AL)",
				"CBS 11 (Anchorage, Alaska)",
				"CBS 11 (Dallas, TX)",
				"CBS 13 (Sacramento, CA)",
				"CBS 13 (Baltimore, MD)",
				"CBS 58 (Milwaukee, WI)",
				"KCTV 5 (Kansas City, MO)",
				"KELO (Sioux Falls, SD)",
				"KLAS 8 (Las Vegas, NV)",
				"KOMV 4 (St. Louis, MO)",
				"KXJB (Fargo, ND)",
				"WANE-TV (Fort Wayne, IN)",
				"WBNS 10 (Columbus, OH)",
				"WGME 13 (Portland, ME)",
				"WINK-TV (Ft. Myers, FL)",
				"WIVB 4 (Buffalo, NY)",
				"WWL-TV 4 (New Orleans, LA)",
				"KCCI 8 (Des Moines, IA)",
				"KHOU 11 (Houston, TX)",
				"KIRO 7 (Seattle, WA)",
				"KOIN 6 (Portland, OR)",
				"KRQE 13 (Albuquerque, NM)",
				"KWCH 12 (Wichita, KS)",
				"WBTV 3 (Charlotte, NC)",
				"WJTV (Jackson, MS)",
				"WLKY (Louisville, KY)",
				"WPRI 12 (Providence, RI)",
				"WTVF 5 (Nashville, TN)"]
			video = dialog.select("Select a Video You Want", video_list)
			__Settings__.setSetting( "video%d" % slot, video_list[video] )
			__Settings__.setSetting( "video%d_url" % slot, "" )
		# FOX
		elif ( channel == 3 ):
			video_list = [
				"FOX 2 (Detroit, MI)",
				"FOX 4 (Dallas-Fort Worth, TX)",
				"FOX 5 (Washington D.C)",
				"FOX 5 (Atlanta, GA)",
				"FOX 5 (New York, NY)",
				"FOX 7 (Austin, TX)",
				"FOX 9 (Minneapolis, MN)",
				"FOX 10 (Phoenix, AZ)",
				"FOX 11 (Los Angeles, CA)",
				"FOX 13 (Tampa, FL)",
				"FOX 13 (Memphis, TN)",
				"FOX 25 (Boston, MA)",
				"FOX 26 (Houston, TX)",
				"FOX 32 (Chicago, IL)",
				"FOX 35 (Orlando, FL)"]
			video = dialog.select("Select a Video You Want", video_list)
			__Settings__.setSetting( "video%d" % slot, video_list[video] )
			__Settings__.setSetting( "video%d_url" % slot, "" )
		# NBC
		elif ( channel == 4 ):
			video_list = [
				"NBC 4 (Los Angeles, CA)",
				"NBC 4 (Washington D.C)",
				"NBC 4 (New York, NY)",
				"NBC 5 (Chicago, IL)",
				"NBC 5 (Dallas-Forth Worth, PA)",
				"NBC 6 (Miami, FL)",
				"NBC 7 (San Diego, CA)",
				"NBC 10 (Philadelphia, PA)",
				"NBC 12 (San Jose, CA)",
				"NBC 30 (Hartford, CT)",
				"WHDH 7 (Boston, MA)",
				"Wood TV8 (Grand Rapids, MI)" ]
			video = dialog.select("Select a Video You Want", video_list)
			__Settings__.setSetting( "video%d" % slot, video_list[video] )
			__Settings__.setSetting( "video%d_url" % slot, "" )

		#__Settings__.openSettings()

	
Main()
