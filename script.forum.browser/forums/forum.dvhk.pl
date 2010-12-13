# Parsing data for forum.dvhk.pl
import:forum.xbmc.org
# The URLs
url:base=http://dvhk.to/
url:forums=index.php
filter:pm_xml_folders=<folder name="Wys.{1,2}ane">(?P<inbox>.+?)</folder>

format:pm_folder=Skrzynka odbiorcza
#Nieprzeczytane Prywatne Wiadomości
filter:pm_counts1=<a href="private.php\?">(?P<display>Prywatne Wiadomo.{1,2}ci</a>: (?:<strong>)?(?P<unread>\d+)(?:</strong>)? nie przeczytanych, razem (?P<total>\d+)).</div>
filter:pm_counts2=Prywatne Wiadomo.{1,2}ci.+?<a href="private.php"[^<>]+?>(?P<unread>\d+)</a>
# The filters
filter:logo=<img src="(?P<suburl>.+?logo.jpg)"[^<>]+? />
filter:forums=(?P<subforum>\s/>\s)*(?<!align="left">)(?:<a href="forumdisplay.php\?).*?f=(?P<forumid>\d+)">(?P<title>.*?)</a>.*?(?:</div><div class="smallfont">(?P<description>.*?)</div>)?
filter:threads=showthread.php\?.*?t=(?P<threadid>\d+)"\sid="thread_title.*?>(?P<title>.*?)</a>.*?window.open\(\'member.php\?.*?u=\d+\', \'_self\'\)">(?P<starter>.*?)</span.*?<a href="member.php.*?t=\d+">(?P<lastposter>.*?)</a>
filter:subscriptions===threads

filter:replies=<table\s.*?id="post\d+.*?<!-- / message -->.*?(?:<!-- sig -->.+?<!-- / sig -->)?

filter:quote=<div class="smallfont" style="margin-bottom:2px">Cytat:</div><table[^<>]*?><tr><td[^<>]*?(?:inset"><div>Napisa.{1,2} <strong>(?P<user>.+?)</strong>(?:</div><div style="font-style:italic)?)?(?:<a href="showthread.php\?[^<>]*?p=(?P<postid>\d+)#\w+\d+" .+?<div style="font-style:italic)?">(?P<quote>(?!<div>).+?)(?:</div>)?</td>.*?</table>

filter:code=<div class.+?>Kod:</div><pre.+?>(?P<code>.+?)</pre>
filter:php=<div class.+?>Kod php:</div>.+?<!-- php buffer start --><code>(?P<php>.+?)</code><!-- php buffer end -->
filter:html=<div class.+?>Kod html:</div><pre.+?>(?P<html>.+?)</pre>

filter:page=>(?P<display>Strona (?P<page>\d+) z (?P<total>\d+))<
filter:next=Nast.{1,2}pna Strona - Results ([\d,]+) to ([\d,]+) of ([\d,]+).*?(?P<page>Nast.{1,2}pna Strona - Results [\d,]+ to [\d,]+ of [\d,]+)
filter:prev=Poprzednia Strona - Results ([\d,]+) to ([\d,]+) of ([\d,]+).*?(?P<page>Poprzednia Strona - Results [\d,]+ to [\d,]+ of [\d,]+)

theme:window_bg=FF1F201B
theme:title_bg=FF2F302B
theme:title_fg=FFFFFFFF
theme:desc_fg=FF66CCFF
theme:post_code=FF99FF99
theme:mode=dark

format:login_required=True
format:language=pl

## Smilies ####################################
# regex should return smile groups that are represented below
smilies:regex=<img[^<>]+?src="images/smilies/(?P<smiley>\w+)\.\w+"[^<>]+?/>
smilies:color=FF999900
# the group match translation
smilies:newsmile=:)
smilies:newtongue=:p
smilies:newwink=;)
smilies:newbiggrin=:D
smilies:newwub=:o
smilies:newsad=:(
smilies:newunsure=%)
smilies:newblink=:eek:
smilies:newcool=:cool:
smilies:newrolleyes=:rolleyes:
smilies:newmad=X-(
