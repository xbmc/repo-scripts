<h1>Fritz!Box SmartHome - Switching Your FritzDECT</h1>
<h2>Anmerkungen zur Integration in den Confluence Skin</h2>

Das Plugin ist als Widget konzipiert, welches im Home unter dem Punkt Programme abgelegt wird. Damit steht es unmittelbar nach dem Start von Kodi zur Verfügung und die Steckdosen sind mit wenigen Aktionen der Fernbedienung erreichbar.

Dazu muss es allerdings zunächst in den Einstellungen konfiguriert werden. AVM verlangt ab OS > 6.50 eine full qualified Authentication (Nutzer, Passwort). Es empfiehlt sich, für Smart Home einen eigenen Nutzer anzulegen und hier zu verwenden (Sniffing).

Zum Einbinden in den Confluence sind einige Änderungen am Skin erforderlich.

* Kopieren des Widgets in den Confluence Skin:

```
cd /usr/share/kodi/addons/skin.confluence/720p
```
bis Kodi Jarvis (V16.x):
```
sudo cp $HOME/.kodi/addons/script.program.fritzact/resources/Confluence/script-fritzact.v16.xml script-fritzact.xml
```
Ab Kodi Krypton wird als Standardskin Estuary/Estouchy verwendet. Confluence muss aus einem Repository installiert werden, die Dateien liegen daher im Addon-Verzeichnis der Installation:
```
cd $HOME/.kodi/addons/skin.confluence/720p
cp $HOME/.kodi/addons/script.program.fritzact/resources/Confluence/script-fritzact.v17.xml script-fritzact.xml
```

* Einbinden der XML-Datei als Include in den Home-Bereich (Jarvis)

```
sudo nano includes.xml
```
bzw. Krypton:
```
nano Includes.xml
```
und unterhalb der Zeile `<include file="IncludesHomeRecentlyAdded.xml" />` folgendes einfügen:

    <include file="script-fritzact.xml" />
    
* Das Include im Hauptfenster anmelden

```
sudo nano IncludesHomeRecentlyAdded.xml
```

  und innerhalb der ControlGroup mit der ID 9003 folgenden Eintrag (als neue Zeile) hinzufügen:
   
```
<include>SmartHome</include>
```
   
   
   Beispiel:
   
```
<?xml version="1.0" encoding="UTF-8"?>
<includes>
  <include name="HomeRecentlyAddedInfo">
      <control type="group" id="9003">
          <include>SmartHome</include>
          <onup>20</onup>
          ...
```


     
Auf eine Anfrage an die FritzBox mit dem Parameter `getdevicelistinfos` antwortet diese mit folgendem XML:
 
```
<devicelist version="1">
    <device identifier="08761 0287125" id="16" 
        functionbitmask="896" fwversion="03.37" manufacturer="AVM"
        productname="FRITZ!DECT 200">
        <present>1</present>
        <name>Steckdose Wohnzimmer (Lampe)</name>
        <switch>
            <state>1</state>
            <mode>manuell</mode>
            <lock>0</lock>
        </switch>
        <powermeter>
            <power>0</power>
            <energy>26</energy>
        </powermeter>
        <temperature>
            <celsius>240</celsius>
            <offset>0</offset>
        </temperature>
     </device>
     <device...>...</device>
</devicelist>
```
    
weitere Informationen (AVM): https://avm.de/fileadmin/user_upload/Global/Service/Schnittstellen/AHA-HTTP-Interface.pdf

<h2>Properties</h2>

    ListItem.Label                      Name des Aktors
    ListItem.Label2                     AIN
    ListItem.Icon                       Zustandsbild des Aktors (offline/an/aus)
    ListItem.Property(type)             Aktor-Typ (switch/thermostat/repeater/group)
    ListItem.Property(present)          Gerät offline/online internationalisiert (siehe strings.po)
    ListItem.Property(state)            Schalter an/aus internationalisiert
    ListItem.Property(b_present)        offline/online als 'boolscher' String (true/false)
    ListItem.Property(b_state)          an/aus als 'boolscher' String (true/false)
    ListItem.Property(mode)             Betriebsmodus auto/manuell deutsch
    ListItem.Property(temperature)      Temperatur des Sensors in Celsius
    ListItem.Property(power)            entnommene Leistung in 0.01 W
    ListItem.Property(energy)           Verbrauch seit Inbetriebnahme (Wh)
    
<h2>Properties der Thermostaten</h2>

    ListItem.Property(set_temp)         Eingestellte Solltemperatur
    ListItem.Property(comf_temp)        Komforttemperatur (Aufheiztemperatur)
    ListItem.Property(lowering_temp)    Absenktemperatur

<h2>Methoden/Aufruf</h2>

Toggelt den Aktor:

```
<onclick>RunScript(plugin.program.fritzact,action=toggle&amp;ain=$INFO[ListItem.Label2])</onclick>
```

Möchte man einen beliebigen Button innerhalb eines Skins zum Umschalten eines Aktors einbinden, kann man das auch direkt unter der Angabe der AIN (hier z.B. 08150 1234567) des betreffenden Aktors realisieren. Die AIN des Aktors findet man im Webinterface der Fritzbox im Bereich Smarthome:

```
<control type='button'>
<label>Garage</label>
<onclick>RunScript(plugin.program.fritzact,action=toggle&amp;ain='08150 1234567')</onclick>
</control>
```

Schaltet Aktor ein:

```
<onclick>RunScript(plugin.program.fritzact,action=on&amp;ain=$INFO[ListItem.Label2])</onclick>
```

Schaltet Aktor aus:

```
<onclick>RunScript(plugin.program.fritzact,action=off&amp;ain=$INFO[ListItem.Label2])</onclick>
```
    
Aufruf z.B. für den dynamischen List Content:

```
<content target="programs">plugin://plugin.program.fritzact?ts=$INFO[Window(Home).Property(fritzact.timestamp)]</content>
```

Möchte man nur eine bestimmte Gruppe (switch, thermostat, group) anzeigen lassen, kann man dem dynamischen List Content die entsprechende Gruppe über den Parameter 'type' mitgeben. Ein Repeater wird als Switch eingeordnet.

(ab Version 0.0.14):

```
<content target="programs">plugin://plugin.program.fritzact?ts=$INFO[Window(Home).Property(fritzact.timestamp)]&amp;type=switch</content>
```

Ein Einbinden des Addons in den Skin als Programm-Addon toggelt den bevorzugten Aktor (siehe Settings), d.h. es können bei mehreren Kodi-Instanzen bzw. -installationen auch die zur Installation sinnvollen Aktoren geschaltet werden (z.B Kodi im Wohnzimmer: bevorzugter Aktor ist Aktor im Wohnzimmer, Kodi Kinderzimmer: bevorzugter Aktor ist Aktor im Kinderzimmer usw.). Wird keine bevorzugte AIN im Setup des Addons festgelegt und gibt es mehr als einen Aktor im Smarthome, erscheint eine Liste aller verfügbarer Aktoren, aus denen einer zum Umschalten ausgewählt werden kann.