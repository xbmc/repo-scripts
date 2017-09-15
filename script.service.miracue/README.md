### Already have the add-on and just looking for the list of commands? [List of commands](commands.md)

# Mira Cue: Kodi control over Alexa

This addon is intended to control Kodi using Amazon Alexa.

How is it different from other solutions?

You **only** need Kodi and Alexa. That's it.
**No need for** Heroku / AWS or any of that.

[![youtube video](https://raw.githubusercontent.com/vertolab/kodi-create-repo/master/screenshots/youtube.png)](https://youtu.be/lhT2Eupi0Tc)

## Installation

Only 3 installation steps:

1. [Add Verto Lab source](#add-verto-lab-source) (http://kodi-repo.vertolab.com/)
2. [Install Mira Cue Add-on](#install-mira-cue-add-on)
3. [Pair Mira Cue Addon with Mira Cue Alexa Skill](#pair-mira-cue-kodi-addon-with-mira-cue-alexa-skill)

### Add Verto Lab source

1. Select the **Settings cogwheel**
![image](https://raw.githubusercontent.com/vertolab/kodi-create-repo/master/screenshots/screenshot_1.png)
2. Select **File manager**
![image](https://raw.githubusercontent.com/vertolab/kodi-create-repo/master/screenshots/screenshot_2.png)
3. Select **Add source**
![image](https://raw.githubusercontent.com/vertolab/kodi-create-repo/master/screenshots/screenshot_3.png)
4. Select **&lt;None>**
![image](https://raw.githubusercontent.com/vertolab/kodi-create-repo/master/screenshots/screenshot_4.png)
5. Type **http://kodi-repo.vertolab.com/**, and select **OK**
![image](https://raw.githubusercontent.com/vertolab/kodi-create-repo/master/screenshots/screenshot_5.png)
6. Highlight the lower text box, type **Verto Lab**, and select **OK**
![image](https://raw.githubusercontent.com/vertolab/kodi-create-repo/master/screenshots/screenshot_6.png)
9. Return **back**, then **back** again to the main screen

### Install Mira Cue Add-on

1. Select **Add-ons**
![image](https://raw.githubusercontent.com/vertolab/kodi-create-repo/master/screenshots/screenshot_7.png)
2. Select the **Enter add-on browser**
![image](https://raw.githubusercontent.com/vertolab/kodi-create-repo/master/screenshots/screenshot_8.png)
3. Select **Install from zip file**
![image](https://raw.githubusercontent.com/vertolab/kodi-create-repo/master/screenshots/screenshot_9.png)
4. Select **Verto Lab**
![image](https://raw.githubusercontent.com/vertolab/kodi-create-repo/master/screenshots/screenshot_10.png)
7. Select **script.service.miracue-1.0.1.zip**
![image](https://raw.githubusercontent.com/vertolab/kodi-create-repo/master/screenshots/screenshot_11.png)
8. If asked about add-ons from unknown sources, click **Settings**. Otherwise skip to step 12.
![image](https://raw.githubusercontent.com/vertolab/kodi-create-repo/master/screenshots/screenshot_17.png)
9. Select **Unknown sources** to toggle it to the enabled state
![image](https://raw.githubusercontent.com/vertolab/kodi-create-repo/master/screenshots/screenshot_18.png)
10. Click **Yes**. The Mira Cue add-on does not collect any personal information and certainly does not send it anywhere.
![image](https://raw.githubusercontent.com/vertolab/kodi-create-repo/master/screenshots/screenshot_19.png)
11. Click **back** and repeat steps 3-7.
12. Wait 1-2 minutes for *Add-on installed* notification.
![image](https://raw.githubusercontent.com/vertolab/kodi-create-repo/master/screenshots/screenshot_12.png)
13. Go **back** to the Add-ons screen and select Program add-ons 
![image](https://raw.githubusercontent.com/vertolab/kodi-create-repo/master/screenshots/screenshot_13.png)

### Pair Mira Cue Kodi Addon with Mira Cue Alexa Skill

1. Select **Mira Cue**
![image](https://raw.githubusercontent.com/vertolab/kodi-create-repo/master/screenshots/screenshot_14.png)
2. Ask your Alexa-enabled device to enable the Mira Cue skill: **"Alexa, enable Mira Cue skill"**
    1. If you're having problems with activating the skill via voice, go to your Alexa app and enable the skill through the app.
3. Once the Mira Cue Alexa Skill is enabled, Select **OK**.
![image](https://raw.githubusercontent.com/vertolab/kodi-create-repo/master/screenshots/screenshot_15.png)
4. Ask your Alexa-enabled device to pair with your Kodi: **"Alexa, ask Mira Cue to pair with code XXXX XXXX"** (replace XXXX XXXX with the code that appears in the dialog).
    1. Your pairing code should contain 8 digits. See the marked frame in the following screenshot:
![image](https://raw.githubusercontent.com/vertolab/kodi-create-repo/master/screenshots/screenshot_16.png)
5. Wait for Alexa notification of success and click **OK**.
6. Say *"Alexa, ask Mira Cue to go home"* to return to the main screen

That's it :) Now you can...

### [Give it a try!](commands.md)

 - *"Alexa ask Mira Cue to set volume to 5"*
 - *"Alexa ask Mira Cue to shuffle all music"*
 - [And many more](commands.md)

## General Addon Comments

The addon uses an always-on, encrypted connection to a server which forwards requests from the paired Alexa. In addition, all communication is only one-way (incoming into Kodi) so no sensitive user data is leaving the device. 

To reduce stress on server resources, most processing is done in the addon itself. This allows the community to overview the implementation and suggest improvements.

### Developers
Feel free to fork this repository, make changes and suggest them as improvements via pull requests.

Credits to https://github.com/m0ngr31/kodi-alexa
Some code in this repository is based on kodi-alexa.
