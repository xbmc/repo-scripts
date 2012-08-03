
[B]METHOD USE[/B]

[B]
1. Add required import in your addon.xml[/B]
    <requires>
        . . .
        <import addon="script.module.dialogaddonscan" version="1.0.3"/>
    </requires>

    If XBMC not install "script.module.dialogaddonscan" from Repo or not import DialogAddonScan
    Download version here "http://passion-xbmc.org/addons/"
    And install "script.module.dialogaddonscan-1.0.X.zip" from XBMC Addons Manager and select "Install from zip file"

[B]
2. Test Demo AddonScan[/B]
    from DialogAddonScan import Demo
    # Test simple exemple on module DialogAddonScan
    Demo()

[B]
3. Normal Use AddonScan[/B]

    from time import sleep
    from traceback import print_exc

    from DialogAddonScan import AddonScan, xbmcguiWindowError
    try:
        scan = AddonScan()
        # create dialog
        scan.create( "Heading" )

        for pct in range( 101 ):
            # percentage total
            percent2 = pct

            # percentage of current action
            percent1 = percent2*10
            while percent1 > 100:
                percent1 -= 100

            # not update line1, because is "Heading", if you want update line1
            # line1 = "Heading"

            # update current action on line2.
            line2 = "Progress1 [B]%i%%[/B]   |   Progress2 [B]%i%%[/B]" % ( percent1, percent2 )

            # update dialog
            # All args is optional: [ percent1=int, percent2=int, line1=str, line2=str ]
            scan.update( percent1, percent2, line2=line2 )

            # if is canceled stop
            if scan.iscanceled():
                break

            # wait...
            sleep( .1 )

        # close dialog and auto destroy all controls
        scan.close()
    except xbmcguiWindowError:
        print_exc()
    except:
        print_exc()

[B]
4. AddonScan on background :)[/B]
  - Create lib "test_AddonScanInBackground.py" copy and paste simple exemple "3. Normal Use AddonScan".

  - In your main code or in any function add:
    import os, xbmc
    script = os.path.join( os.getcwd(), "test_AddonScanInBackground.py" )
    xbmc.executebuiltin( "RunScript(%s)" % ( script ) )

  - And now test AddonScan on background :)

[B]
5. Methods Cancel AddonScan[/B]
  - Cancel button on dialog ( Only mouse has ability to cancel )

  - Or in your code test:
   - Example for Normal Use AddonScan:
    scan.canceled = True
    if scan.iscanceled():
        break

   - Example for AddonScan on background:
    # in your module.py
    if xbmc.getInfoLabel( "Window.Property(DialogAddonScan.IsAlive)" ) == "true":
        # ok rajoute un bouton stop dans le context menu
        c_items = [ ( "Stop Addon Scan", "RunPlugin(%s?action=stopscan)" % sys.argv[ 0 ] ) ]
        listitem.addContextMenuItems( c_items )

    # and your main.py
    if "stopscan" in sys.argv[ 2 ]:
        window = xbmcgui.Window( xbmcgui.getCurrentWindowId() )
        window.setProperty( "DialogAddonScan.Cancel", "true" )

[B]
6. Available Data and Window.Property[/B]
  - AddonScan: [bool] AddonScanObject.canceled
  - Window.Property: "DialogAddonScan.Cancel"
  - Window.Property: "DialogAddonScan.IsAlive"
  - Window.Property: "DialogAddonScan.Hide" ( for user settings )

[B]
7. Settings access[/B]
  - Access from your addon settings.xml
    <setting label="Settings Dialog Scan" option="close" type="action" action="Addon.OpenSettings(script.module.dialogaddonscan)" default="" />
    or
    <setting label="Settings Dialog Scan" option="close" type="action" action="RunScript(special://home/addons/script.module.dialogaddonscan/lib/DialogAddonScan.py,opensettins)" default="" />

  - Access from python code
    from xbmcaddon import Addon
    Addon( "script.module.dialogaddonscan" ).openSettings()

  - Available settings id
    - id="hidedialog" type="bool"
    - id="animation"  type="bool"
    - id="custompos"  type="bool"
    - id="customposx" type="slider"
    - id="customposx" type="slider"
