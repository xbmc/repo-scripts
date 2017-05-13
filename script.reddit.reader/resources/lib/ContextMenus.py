import re


from main_listing import GCXM_hasmultipleauthor, GCXM_hasmultiplesubreddit, GCXM_hasmultipledomain, GCXM_actual_url_used_to_generate_these_posts, GCXM_reddit_query_of_this_gui
from default import addon
from reddit import assemble_reddit_filter_string, subreddit_in_favorites #, this_is_a_user_saved_list
from utils import log,translation, colored_subreddit, build_script, truncate

cxm_show_html_to_text     = addon.getSetting("cxm_show_html_to_text") == "true"
cxm_show_open_browser     = addon.getSetting("cxm_show_open_browser") == "true"
cxm_show_comments         = addon.getSetting("cxm_show_comments") == "true"

cxm_show_by_author        = addon.getSetting("cxm_show_by_author") == "true"
cxm_show_by_subreddit     = addon.getSetting("cxm_show_by_subreddit") == "true"
cxm_show_by_domain        = addon.getSetting("cxm_show_by_domain") == "true"

cxm_show_autoplay         = addon.getSetting("cxm_show_autoplay") == "true"
cxm_show_slideshow        = addon.getSetting("cxm_show_slideshow") == "true"

cxm_show_add_shortcuts    = addon.getSetting("cxm_show_add_shortcuts") == "true"


cxm_show_filter           = addon.getSetting("cxm_show_filter") == "true"
cxm_show_search           = addon.getSetting("cxm_show_search") == "true"

cxm_show_youtube_items    = addon.getSetting("cxm_show_youtube_items") == "true"

def build_context_menu_entries(num_comments,commentsUrl, subreddit, domain, link_url, post_id, post_title, posted_by):

    s=truncate(subreddit,15)     #crop long subreddit names in context menu
    colored_subreddit_short=colored_subreddit( s )
    colored_subreddit_full=colored_subreddit( subreddit )
    colored_domain_full=colored_subreddit( domain, 'tan',False )
    post_title_short=truncate(post_title,15)
    post_author=truncate(posted_by,15)

    label_html_to_text=translation(32502)
    label_open_browser=translation(32503)
    label_view_comments=translation(32504)+' ({})'.format(num_comments)
    label_more_by_author=translation(32506).format(author=post_author)
    label_goto_subreddit=translation(32508).format(subreddit=subreddit)
    label_goto_domain=translation(32510).format(domain=domain)
    label_autoplay_after=translation(32513)+' '+colored_subreddit( post_title_short, 'gray',False )

    label_add_to_shortcuts=translation(32516).format(subreddit=subreddit)


    label_search=translation(32520)

    cxm_list=[]
    if cxm_show_html_to_text:
        cxm_list.append((label_html_to_text , build_script('readHTML', link_url)         ))

    if cxm_show_open_browser:
        cxm_list.append((label_open_browser , build_script('openBrowser', link_url)         ))

    if cxm_show_comments:
        cxm_list.append((label_view_comments , build_script('listLinksInComment', commentsUrl )  ))

    if GCXM_hasmultipleauthor and cxm_show_by_author:
        cxm_list.append( (label_more_by_author, build_script("listSubReddit", assemble_reddit_filter_string("","/user/"+posted_by+'/submitted'), posted_by)  ) )

    if GCXM_hasmultiplesubreddit and cxm_show_by_subreddit:
        cxm_list.append( (label_goto_subreddit, build_script("listSubReddit", assemble_reddit_filter_string("",subreddit), subreddit)  ) )

    if GCXM_hasmultipledomain and cxm_show_by_domain:
        cxm_list.append( (   label_goto_domain, build_script("listSubReddit", assemble_reddit_filter_string("",'','',domain), domain)  ) )

    if any(x in GCXM_actual_url_used_to_generate_these_posts.lower() for x in ['/random','/randnsfw']): #if '/rand' in GCXM_actual_url_used_to_generate_these_posts:
        cxm_list.append( (translation(32511) +' random', build_script('listSubReddit', GCXM_actual_url_used_to_generate_these_posts)) , )  #Reload

    if cxm_show_autoplay:
        cxm_list.extend( [
                        (translation(32512)    , build_script('autoPlay', GCXM_reddit_query_of_this_gui)),
                        (label_autoplay_after  , build_script('autoPlay', GCXM_reddit_query_of_this_gui.split('&after=')[0]+'&after='+post_id)),
                        ])

    if cxm_show_slideshow:
        cxm_list.append( (translation(32514)    , build_script('autoSlideshow', GCXM_reddit_query_of_this_gui)) )

    if not subreddit_in_favorites(subreddit) and cxm_show_add_shortcuts:
        cxm_list.append( (label_add_to_shortcuts, build_script("addSubreddit", subreddit)  ) )

    if cxm_show_filter:
        cxm_list.append( (translation(32519).format(colored_subreddit_short), build_script("addtoFilter", subreddit,'','subreddit')  ) )
        cxm_list.append( (translation(32519).format(colored_domain_full)    , build_script("addtoFilter", domain,'','domain')  ) )

    if cxm_show_search:
        if GCXM_hasmultiplesubreddit:
            cxm_list.append( (label_search        , build_script("search", '', '')  ) )
        else:
            label_search+=' {}'.format(colored_subreddit_full)
            cxm_list.append( (label_search        , build_script("listSubReddit", '', subreddit)  ) )


    if cxm_show_youtube_items:
        cxm_list.extend( build_youtube_context_menu_entries('', link_url, video_id=None ))

    return cxm_list

def build_youtube_context_menu_entries(type_, youtube_url,video_id=None):
    from domains import ClassYoutube
    cxm_list=[]

    match=re.compile( ClassYoutube.regex, re.I).findall( youtube_url )  #regex='(youtube.com/)|(youtu.be/)|(youtube-nocookie.com/)|(plugin.video.youtube/play)'
    if match:

        if not video_id:
            video_id=ClassYoutube.get_video_id(youtube_url)

        channel_id_from_url=ClassYoutube.get_channel_id_from_url(youtube_url)

        if type_=='channel': #no need to list the "show more videos from this channel" entry if we're already showing "videos from this channel"
            cxm_list.append( (translation(32523)  , build_script("listRelatedVideo", youtube_url, '', 'related')  ) )
        else:
            cxm_list.append( (translation(32522)  , build_script("listRelatedVideo", youtube_url, '', 'channel')  ) )
            if video_id and not channel_id_from_url:#if we can parse channel id from url, and there is no video id, the url is for a channel. skip showing related videos
                cxm_list.append( (translation(32523)  , build_script("listRelatedVideo", youtube_url, '', 'related')  ) )

        if video_id:
            cxm_list.append( (translation(32524)    , build_script("listSubReddit", assemble_reddit_filter_string(video_id,'','',''), 'Search')  ) )

    return cxm_list

if __name__ == '__main__':
    pass