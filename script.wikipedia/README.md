## Wikipedia Scripted Window
Create the following xml dialog in your skin

```
script-wikipedia.xml
```

```xml
<?xml version="1.0" encoding="UTF-8"?>
<window type="dialog">
    <defaultcontrol always="true">9902</defaultcontrol>
    <controls>
        <!-- CONTENT GOES HERE -->
    </controls>
</window>
```

## Required Controls

| ID | Type | Description |
| :--- | :--- | :--- |
| 9901 | label | Title of the Wikipedia article |
| 9902 | list | List of sections containing the table of contents. Scrolling the list changes text loaded in the section textbox 9903. Clicking a listitem opens a select dialog for page links in the section |
| 9903 | textbox | Textbox with the text of the section focused in 9902 |
| 9904 | label | Creative commons attribution label. REQUIRED! You MUST display this text as per Wikipedia licensing requirements |
| 9905 | image | Creative commons licence logo. The license logo is optional as long as you display the attribution label |
| 61 | scrollbar | Page control for section textbox. Clicking the scrollbar will pop-up select dialog for page links in the section |

## Window Properties

| Property | Description |
| :--- | :--- |
| Window.Property(Backdrop) | First result found on wikimedia commons for search term with landscape aspect. Not always accurate but can be useful to use in place of background fanart. This image is aliased to Window(Home).Property(Wikipedia.Backdrop) if you need to use it in a window underneath the dialog. |
| Window.Property(Image) | If the current section has an image, the first image will be added to this property. Otherwise it gets the first image for the page |
| Window.Property(ImageText) | The alt text for the image which is displayed on wikipedia for vision impaired users or when the image does not load |


## Changing Tag Formatting

HTML tag text formatting can be modified using a skin string.

Example: Change all `<a href=>` hyperlinks to red
`Skin.SetString(Wikipedia.Format.Link,[COLOR=red]{}[/COLOR])`

The `{}` curly braces will be replaced with the text between the HTML tags

| Skin String | Affected HTML Tags |
| :--- | :--- |
| Wikipedia.Format.Link | `<a href=>` |
| Wikipedia.Format.Bold | `<hx> <b> <th> and class:mw-headline` |
| Wikipedia.Format.Emphasis | `<em> <i>` |
| Wikipedia.Format.Superscript | `<sup>` |

## Opening / Searching

```
RunScript(script.wikipedia,wikipedia=SEARCHTERM)
```

Searches wikipedia for the search term and provides a select dialog for user to select from results.

Optionally can add a `tmdb_type=TYPE` param to tailor the search for more relevant results  
Optionally can add a `xml_file=FILENAME` param to use alternate skin template  
Optionally can add a `language=CODE` param to set language with two letter ISO 639-1 code

Supported language codes: `it` `de` `fr` `es` `en`

```
RunScript(script.wikipedia,wikipedia=Alien,tmdb_type=movie,language=en)
RunScript(script.wikipedia,wikipedia=Chernobyl,tmdb_type=tv,language=en)
RunScript(script.wikipedia,wikipedia=Matt Smith,tmdb_type=person,language=en)
```
