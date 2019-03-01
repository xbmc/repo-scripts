INFO FOR SKINNERS - How to use this addon in your skin:


1) Create a custom dialog and add this code:
	<onload>RunScript(script.check.theme)</onload>
    <visible>System.IdleTime(1)</visible>
    <visible>!ListItem.IsCollection + !String.Contains(ListItem.Path,thumb:) + !String.Contains(ListItem.Path,image:) + !String.Contains(ListItem.Path,plugin) + !String.Contains(ListItem.Path,videodb:)</visible>
    <visible>Container.Content(movies) | [Container.Content(tvshows) + !Player.Playing] | [Container.Content(seasons) + !Player.Playing]</visible>
    <visible>!Window.IsActive(movieinformation)</visible>
    <visible>Window.IsActive(videos)</visible>

2) To check if a mp3 theme is available this property will be set to true:
	$INFO[Window(Home).Property(theme_ready)]
