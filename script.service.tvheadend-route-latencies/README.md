Tvheadend route latencies
=========================
This Kodi add-on shows latency (RTT) and packets loss to consecutive steps on the way from Kodi to Tvheadend server. It can be used when network quality cause problems during watching TV streaming from Tvheadend. The problem can be in:
  * Kodi computer's local network,
  * connection between Kodi computer's local network and its Internet Service Provider (ISP),
  * connection between Tvheadend computer's local network and its ISP,
  * Tvheadend computer's local network,
  * the route between both ISPs.

Checking the aforementioned points will give you a clue where is the problem and which network should be fixed.
Add-on works by analogy to traceroute. However the whole route is not important. Latencies and package lose in both Kodi's and Tvheadend's local networks and connections to ISP providers are important. Route between both ISPs is not important since it can be handled by ISPs themselves.

To run this add-on you will need *Tvheadend HTSP client* add-on.

Installation
------------
Add-on can be installed on Windows, Linux (including LibreELEC) and Android (including Android TV).

~~Add-on can be installed in a standard way from the standard Kodi repository.~~
~~1. Make sure that you have *Tvheadend HTSP client* add-on.~~
~~2. In Kodi go to *Add-ons > Download > Install from repository > Program add-ons*.~~
~~3. Select *Tvheadend route latencies* add-on.~~
~~4. Press *Install* button.~~

If you want to run this add-on then:
1. Download the add-on in [a zip file](https://github.com/iwis/script.service.tvheadend-route-latencies/archive/master.zip).
2. Inside the zipped file rename *script.service.tvheadend-route-latencies-master* directory to *script.service.tvheadend-route-latencies*.
3. Rename *script.service.tvheadend-route-latencies-master.zip* file to *script.service.tvheadend-route-latencies.zip*
4. Install add-on from the zip file.

Usage
-----
1. It is best to test latencies while watching TV thus play some channel from Tvheadend server.
2. Run *Tvheadend route latencies* add-on by selecting it in *Add-ons > Program add-ons > Tvheadend route latencies*.
3. After displaying dialog box wait about 30 seconds for the results.
4. You can press *Check* button to check latencies again if you want.
5. In the settings you can change:
  * *Test length* - how long the test will take, the default is 30 seconds,
  * *Test concurrently* - whether all devices will be tested concurrently (4x faster) or not, the default is *On*,
  * *Address of nearby server in the Internet* - address of a device tested in the second step, the default is facebook.com.

<img src="https://raw.githubusercontent.com/iwis/script.service.tvheadend-route-latencies/master/resources/screenshot-01.jpg" alt="Screenshot" width="683" height="384">

Detailed description
--------------------
The tested steps on the way from Kodi to Tvheadend server are:
1. A router in the network that computer with Kodi belongs to - pinging it will tell us about health of Kodi's local network.
2. Some nearby computer in the Internet. You can use tracert to discover a server owned by your ISP and then set it in the settings. facebook.com is the default address since Facebook has many servers around the world so there is a change that one of them is near you. If latency in the first step is low then large latency in this step suggests that problem is with the connection to Kodi's ISP.
3. Router in the network that computer with Tvheadend belongs to - if latencies in the previous steps are low then large latency in this step suggests that problem is with connection between Tvheadend computer's local network and its ISP.
4. Computer with installed Tvheadend. If it is in a small home network it will not have a public IP address so we cannot ping it from the Internet. This is why we are measuring time that Tvheadend HTTP server needs to give us an answer. If latencies in the previous steps were low then large latency in this step suggests that problem is in the Tvheadend server local network.

If both: computer with Tvheadend and computer with Kodi are in the same local network then situation is simpler.

If Tvheadend's LAN and both connections to ISPs are not wireless and if Tvheadend server is in the same city as Kodi device then you can obtain the following latencies:
  * 1st step: 4 ms
  * 2nd step: 11 ms
  * 3rd step: 14 ms
  * 4th step: 16 ms

Generally, the following latencies are incorrect:
  * 1st step: > 20 ms
  * 2nd step: > 60 ms
  * 3rd step: > 60 ms (+ 30-60 ms if Tvheadend server and Kodi computer are on different continents)
  * 4th step: > 60 ms (+ 30-60 ms if Tvheadend server and Kodi computer are on different continents)

More than 5% packets lost in any step is also incorrect.

In Android (and Android TV) there is no information about Gateway in Kodi > System information > Network > Gateway. This is why the first step is not tested.

Support
-------
Support at the Kodi forum: [forum.kodi.tv/showthread.php?tid=313838](http://forum.kodi.tv/showthread.php?tid=313838)

Development
-----------
Add-on was tested on Kodi 17 and on the following operating systems:
  * Windows 10 32-bit
  * Linux Mint 18.1 64-bit
  * LibreELEC 8
  * Android 7.0
  * Android TV 6

Latencies measured in 4th step on tested smartphone with Android were larger than on other devices. I do not know what was the reason.

If you want to run this add-on on macOS or iOS then:
1. Download the add-on in a zip file.
2. Set `<platform>all</platform>` in addon.xml file.
3. Install add-on from a zip file.
4. Test if it works well.

