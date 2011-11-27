Python wrapper for the Brightcove read-only API.

```python
from brightcove.api import Brightcove

TOKEN = 'myreadonlytoken.'
b = Brightcove(TOKEN)
videos = b.find_all_videos()
```

See:

* http://support.brightcove.com/en/docs/getting-started-media-api
* http://docs.brightcove.com/en/media/
