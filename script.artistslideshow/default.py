import resources.lib.artistslideshow as ArtistSlideshow

if (__name__ == "__main__"):
    slideshow = ArtistSlideshow.Main()
    if slideshow.RunFromSettings():
        slideshow.DoSettingsRoutines()
    elif not slideshow.SlideshowRunning():
        slideshow.Start()
