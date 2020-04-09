# -*- coding: utf-8 -*-
class YoutubeTemplates:

    @property
    def not_connected(self):
        return '''<service xmlns="urn:dial-multiscreen-org:schemas:dial">
                    <name>YouTube</name>
                    <options allowStop="true"/>
                    <state>stopped</state>
                </service>'''

    @property
    def connected(self):
        return '''<service xmlns="urn:dial-multiscreen-org:schemas:dial">
                    <name>YouTube</name>
                    <options allowStop="true"/>
                    <servicedata xmlns="urn:chrome.google.com:cast">
                        <connectionSvcURL></connectionSvcURL>
                        <protocols>
                            <protocol>ramp</protocol>
                        </protocols>
                    </servicedata>
                    <state>running</state>
                    <activity-status xmlns="urn:chrome.google.com:cast">
                        <description>YouTube Receiver</description>
                    </activity-status>
                    <link rel="run" href="web-1"/>
                </service>'''

    @staticmethod
    def announcement(screen_uid, default_screen_name, default_screen_app):
        return {"device": "LOUNGE_SCREEN",
                "id": screen_uid,
                "name": default_screen_name,
                "app": default_screen_app,
                "theme": "cl",
                "capabilities": "",
                "mdx-version": "2",
                "loungeIdToken": "",
                "VER": "8",
                "v": "2",
                "RID": "1337",
                "AID": "42",
                "zx": "xxxxxxxxxxxx",
                "t": "1"}
