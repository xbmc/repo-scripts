# Movies On The Run (MOTR) Kodi Client

Makes you able to access your MOTR server through Kodi

## Getting started

Download the latest release of the MOTR server: https://github.com/large/MOTRd/releases
(Please note that the installer is not signed atm. I cannot afford a cert, this is just a hobby)

Install server, create a user, make sure to remember the port you selected (default 80 unsecure).
Login as admin, select directories you want to share.

In Kodi client:
Enter your servers IP or hostname, port then username and password.
You should see the folders you selected.

## Test setup

If you just want to see how the addon work, please setup your client as follow

Server: test.motr.pw
Port: 880 (Unsecured or 4444 with TLS)
Username: test
Password: welcome

If that is not reachable, test in your browser
http://test.motr.pw:880/
https://test.motr.pw:4444/

You should see a loginpage in the browser.
Contact lars@werner.no if not
