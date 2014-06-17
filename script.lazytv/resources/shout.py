'''  A simple script that allows you to let the author know that the addon is being used. Its nice to feel appeciated! '''

import smtplib
from email.mime.text import MIMEText
import xbmcaddon
import time

thyme = time.time()

recipient = 'subliminal.karnage@gmail.com'

body = '<table border="1">'
body += '<tr><td>%s</td></tr>' % "I'm using the addon!"
body += '</table>'

msg = MIMEText(body, 'html')
msg['Subject'] = 'LazyTV +1  %s' % thyme
msg['From'] = 'LazyTV'
msg['To'] = recipient
msg['X-Mailer'] = 'LazyTV Shout Out %s' % thyme

smtp = smtplib.SMTP('alt4.gmail-smtp-in.l.google.com')
smtp.sendmail(msg['From'], msg['To'], msg.as_string(9))
smtp.quit()


_addon_ = xbmcaddon.Addon('script.lazytv')
_addon_.setSetting(id="shout",value='true')
