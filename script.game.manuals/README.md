# script.game.manuals

Shows the manual that came with a game, and finds one for a game that has none.

    RunScript(script.game.manuals,game=<path>[,title=<name>][,manual=<path>])

A skin calls it from its game OSD or info screen, passing what it knows with
`$ESCINFO[]` so commas and brackets in a name survive:

    RunScript(script.game.manuals,game=$ESCINFO[Player.FilenameAndPath],title=$ESCINFO[RetroPlayer.Title])

The title is what the game is called on screen, and a hint for providers.
`RetroPlayer.Title` is the playing game's own title, which a library sets;
when it is empty the title comes from the file name, tags removed. It also adds **Manual**
to a game's context menu, titled with the item's label.

## Where manuals are found

Beside the game, or in a `manuals` (or `Manuals`) folder next to it, named
like the game with `.pdf`, `.cbz` or `.cbr`. Names are also compared with their
bracketed tags removed, so `Sonic The Hedgehog 2 (World) (Rev A).md` finds
`Sonic The Hedgehog 2 (USA, Europe).pdf`.

PDFs are shown through [vfs.pdf](https://github.com/sunlollyking/vfs.pdf),
which this depends on; comic archives through Kodi's own zip and rar support.

## Finding one

A game with no manual opens a search. A manual provider is an ordinary plugin
whose id starts with `plugin.game.manuals.`, and is called the way Kodi calls
a subtitle service:

    plugin://<provider>/?action=search&path=<game>&title=<name>

Each result's path is the manual, which is downloaded into the `manuals` folder
beside the game, or into this add-on's profile folder when that can't be
written to. [plugin.game.manuals.regvault](https://github.com/sunlollyking/plugin.game.manuals.regvault)
is one.

## Reading

| | Whole page | Zoomed in |
|---|---|---|
| Left / right | Turn the page | Move around it |
| Up / down | | Move around it |
| Bumpers, triggers, page up / down | Turn the page | Turn the page |
| Select | Zoom in | Back to the whole page |
| Mouse wheel, zoom keys | Zoom | Zoom |

Each manual reopens at the page it was left on.

## Skins

The windows are `script-game-manuals-viewer.xml` and
`script-game-manuals-finder.xml`. A skin can provide its own.

The viewer's page is image control 100. Its position and size in the skin are
the area the page is fitted to and moved around in; the add-on then moves and
resizes the control itself. It publishes `Window.Property(title)`,
`Window.Property(page)` and `Window.Property(zoomed)`.

The finder's results are list 200, and its buttons are 300 (ask the next
provider, worth showing when `Window.Property(providers)` is more than 1), 310
(get more providers) and 320 (cancel). It publishes `Window.Property(state)` -
`searching`, `results`, `empty`, `noproviders`, `downloading` or `failed` -
along with `game`, `provider`, `provider.icon`, `status`, `hint` and
`progress`. Images 400 and 410 are an optional download bar: the add-on sizes
410 to a share of 400's width. Each result carries the provider's `manual.*`
properties.

## Tests

    python3 -m pytest tests
