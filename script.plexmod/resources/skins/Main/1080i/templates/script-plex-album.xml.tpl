{% extends "default.xml.tpl" %}
{% block headers %}<defaultcontrol>100</defaultcontrol>{% endblock %}
{% block content %}
    <control type="group" id="50">
        <posx>0</posx>
        <posy>{{ vscale(135) }}</posy>
        <defaultcontrol>101</defaultcontrol>

        <control type="group">
            <posx>60</posx>
            <posy>0</posy>
            <control type="label">
                <posx>0</posx>
                <posy>5</posy>
                <width>420</width>
                <height>{{ vscale(40) }}</height>
                <font>font13</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <label>$INFO[Window.Property(artist.title)]</label>
            </control>
            <control type="label">
                <posx>0</posx>
                <posy>{{ vscale(60) }}</posy>
                <width>420</width>
                <height>{{ vscale(40) }}</height>
                <font>font13</font>
                <align>left</align>
                <aligny>center</aligny>
                <textcolor>FFFFFFFF</textcolor>
                <label>$INFO[Window.Property(album.title)]</label>
            </control>
            <control type="image">
                <posx>0</posx>
                <posy>{{ vscale(142) }}</posy>
                <width>630</width>
                <height>{{ vscale(630) }}</height>
                <texture>$INFO[Window.Property(album.thumb)]</texture>
                <aspectratio>scale</aspectratio>
            </control>
        </control>

        {% block buttons %}
            <control type="grouplist" id="300">
                <animation effect="fade" start="0" end="100" time="200" reversible="true">VisibleChange</animation>
                <defaultcontrol>301</defaultcontrol>
                <posx>50</posx>
                <posy>{{ vscale(784) }}</posy>
                <width>650</width>
                <height>{{ vscale(145) }}</height>
                <onup>200</onup>
                <onright>101</onright>
                <itemgap>-50</itemgap>
                <orientation>horizontal</orientation>
                <align>center</align>
                <scrolltime tween="quadratic" easing="out">200</scrolltime>
                <usecontrolcoords>true</usecontrolcoords>

                {% with attr = {"width": 174, "height": 139} & template = "includes/themed_button.xml.tpl" & hitrect = {"w": 94, "h": 59} %}
                    {% include template with name="play" & id=301 %}
                    {% include template with name="shuffle" & id=302 %}
                    {% include template with name="more" & id=303 %}
                {% endwith %}

            </control>
        {% endblock %}

        <control type="group" id="100">
            <visible>Integer.IsGreater(Container(101).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
            <defaultcontrol>101</defaultcontrol>
            <posx>750</posx>
            <posy>0</posy>
            <width>1170</width>
            <height>{{ vscale(945) }}</height>
            <control type="image">
                <posx>0</posx>
                <posy>0</posy>
                <width>1380</width>
                <height>{{ vscale(945) }}</height>
                <texture>script.plex/white-square.png</texture>
                <colordiffuse>20000000</colordiffuse>
            </control>
            <control type="list" id="101">
                <hitrect x="40" y="0" w="1090" h="945" />
                <posx>0</posx>
                <posy>0</posy>
                <width>1170</width>
                <height>{{ vscale(945) }}</height>
                <onup>200</onup>
                <onright>152</onright>
                <onleft>300</onleft>
                <scrolltime>200</scrolltime>
                <orientation>vertical</orientation>
                <preloaditems>4</preloaditems>
                <pagecontrol>152</pagecontrol>
                <!-- ITEM LAYOUT ########################################## -->
                <itemlayout height="{{ vscale(76) }}">
                    <control type="group">
                        <visible>String.IsEmpty(ListItem.Property(is.header))</visible>
                        <posx>120</posx>
                        <posy>{{ vscale(24) }}</posy>
                        <control type="label">
                            <visible>!String.IsEqual(ListItem.Property(track.ID),Window(10000).Property(script.plex.track.ID))</visible>
                            <posx>-10</posx>
                            <posy>0</posy>
                            <width>60</width>
                            <height>{{ vscale(76) }}</height>
                            <font>font10</font>
                            <align>center</align>
                            <aligny>center</aligny>
                            <textcolor>D8FFFFFF</textcolor>
                            <label>[B]$INFO[ListItem.Property(track.number)][/B]</label>
                        </control>
                        <control type="image">
                            <visible>String.IsEqual(ListItem.Property(track.ID),Window(10000).Property(script.plex.track.ID))</visible>
                            <posx>2</posx>
                            <posy>{{ vscale(21) }}</posy>
                            <width>35</width>
                            <height>{{ vscale(35) }}</height>
                            <texture>script.plex/indicators/playing-circle.png</texture>
                            <colordiffuse>FFE5A00D</colordiffuse>
                        </control>
                        <control type="group">
                            <posx>90</posx>
                            <posy>0</posy>
                            <control type="label">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>723</width>
                                <height>{{ vscale(76) }}</height>
                                <font>font10</font>
                                <align>left</align>
                                <aligny>center</aligny>
                                <textcolor>FFFFFFFF</textcolor>
                                <label>[B]$INFO[ListItem.Label][/B]</label>
                            </control>
                        </control>
                        <control type="label">
                            <posx>730</posx>
                            <posy>0</posy>
                            <width>200</width>
                            <height>{{ vscale(76) }}</height>
                            <font>font10</font>
                            <align>right</align>
                            <aligny>center</aligny>
                            <textcolor>D8FFFFFF</textcolor>
                            <label>[B]$INFO[ListItem.Property(track.duration)][/B]</label>
                        </control>
                        <control type="image">
                            <visible>String.IsEmpty(ListItem.Property(is.footer))</visible>
                            <posx>0</posx>
                            <posy>{{ vscale(73) }}</posy>
                            <width>930</width>
                            <height>{{ vscale(2) }}</height>
                            <texture>script.plex/white-square.png</texture>
                            <colordiffuse>40000000</colordiffuse>
                        </control>
                    </control>

                    <control type="label">
                        <visible>!String.IsEmpty(ListItem.Property(is.header))</visible>
                        <posx>120</posx>
                        <posy>{{ vscale(24) }}</posy>
                        <width>400</width>
                        <height>{{ vscale(76) }}</height>
                        <font>font10</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>FFFFFFFF</textcolor>
                        <label>[B][UPPERCASE]$INFO[ListItem.Label][/UPPERCASE][/B]</label>
                    </control>

                </itemlayout>

                <!-- FOCUSED LAYOUT ####################################### -->
                <focusedlayout height="{{ vscale(76) }}">
                    <control type="group">
                        <visible>String.IsEmpty(ListItem.Property(is.header))</visible>
                        <control type="group">
                            <visible>!Control.HasFocus(101)</visible>
                            <posx>120</posx>
                            <posy>{{ vscale(24) }}</posy>
                            <control type="label">
                                <visible>!String.IsEqual(ListItem.Property(track.ID),Window(10000).Property(script.plex.track.ID))</visible>
                                <posx>-10</posx>
                                <posy>0</posy>
                                <width>60</width>
                                <height>{{ vscale(76) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <aligny>center</aligny>
                                <textcolor>D8FFFFFF</textcolor>
                                <label>[B]$INFO[ListItem.Property(track.number)][/B]</label>
                            </control>
                            <control type="image">
                                <visible>String.IsEqual(ListItem.Property(track.ID),Window(10000).Property(script.plex.track.ID))</visible>
                                <posx>2</posx>
                                <posy>{{ vscale(21) }}</posy>
                                <width>35</width>
                                <height>{{ vscale(35) }}</height>
                                <texture>script.plex/indicators/playing-circle.png</texture>
                                <colordiffuse>FFE5A00D</colordiffuse>
                            </control>
                            <control type="group">
                                <posx>90</posx>
                                <posy>0</posy>
                                <control type="label">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>723</width>
                                    <height>{{ vscale(76) }}</height>
                                    <font>font10</font>
                                    <align>left</align>
                                    <aligny>center</aligny>
                                    <textcolor>FFFFFFFF</textcolor>
                                    <label>[B]$INFO[ListItem.Label][/B]</label>
                                </control>
                            </control>
                            <control type="label">
                                <posx>730</posx>
                                <posy>0</posy>
                                <width>200</width>
                                <height>{{ vscale(76) }}</height>
                                <font>font10</font>
                                <align>right</align>
                                <aligny>center</aligny>
                                <textcolor>D8FFFFFF</textcolor>
                                <label>[B]$INFO[ListItem.Property(track.duration)][/B]</label>
                            </control>
                            <control type="image">
                                <visible>String.IsEmpty(ListItem.Property(is.footer))</visible>
                                <posx>0</posx>
                                <posy>{{ vscale(73) }}</posy>
                                <width>930</width>
                                <height>{{ vscale(2) }}</height>
                                <texture>script.plex/white-square.png</texture>
                                <colordiffuse>40000000</colordiffuse>
                            </control>
                        </control>

                        <control type="group">
                            <visible>Control.HasFocus(101)</visible>
                            <posx>63</posx>
                            <posy>{{ vscale(21) }}</posy>
                            <control type="image">
                                <posx>-40</posx>
                                <posy>{{ vscale(-40) }}</posy>
                                <width>1130</width>
                                <height>{{ vscale(156) }}</height>
                                <texture border="40">script.plex/square-rounded-shadow.png</texture>
                            </control>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>1044</width>
                                <height>{{ vscale(76) }}</height>
                                <texture border="12">script.plex/white-square-rounded.png</texture>
                                <colordiffuse>FFE5A00D</colordiffuse>
                            </control>
                            <control type="label">
                                <visible>!String.IsEqual(ListItem.Property(track.ID),Window(10000).Property(script.plex.track.ID))</visible>
                                <posx>48</posx>
                                <posy>0</posy>
                                <width>50</width>
                                <height>{{ vscale(76) }}</height>
                                <font>font12</font>
                                <align>left</align>
                                <aligny>center</aligny>
                                <textcolor>B8000000</textcolor>
                                <label>[B]$INFO[ListItem.Property(track.number)][/B]</label>
                            </control>
                            <control type="image">
                                <visible>String.IsEqual(ListItem.Property(track.ID),Window(10000).Property(script.plex.track.ID))</visible>
                                <posx>36</posx>
                                <posy>{{ vscale(21) }}</posy>
                                <width>35</width>
                                <height>{{ vscale(35) }}</height>
                                <texture>script.plex/indicators/playing-circle.png</texture>
                                <colordiffuse>FF000000</colordiffuse>
                            </control>
                            <control type="group">
                                <posx>140</posx>
                                <posy>0</posy>
                                <control type="label">
                                    <posx>0</posx>
                                    <posy>0</posy>
                                    <width>738</width>
                                    <height>{{ vscale(76) }}</height>
                                    <font>font12</font>
                                    <align>left</align>
                                    <aligny>center</aligny>
                                    <textcolor>DF000000</textcolor>
                                    <label>[B]$INFO[ListItem.Label][/B]</label>
                                </control>
                            </control>
                            <control type="label">
                                <posx>796</posx>
                                <posy>0</posy>
                                <width>200</width>
                                <height>{{ vscale(76) }}</height>
                                <font>font12</font>
                                <align>right</align>
                                <aligny>center</aligny>
                                <textcolor>B8000000</textcolor>
                                <label>[B]$INFO[ListItem.Property(track.duration)][/B]</label>
                            </control>
                        </control>
                    </control>

                    <control type="label">
                        <visible>!String.IsEmpty(ListItem.Property(is.header))</visible>
                        <posx>120</posx>
                        <posy>{{ vscale(24) }}</posy>
                        <width>400</width>
                        <height>{{ vscale(76) }}</height>
                        <font>font10</font>
                        <align>left</align>
                        <aligny>center</aligny>
                        <textcolor>FFFFFFFF</textcolor>
                        <label>[B][UPPERCASE]$INFO[ListItem.Label][/UPPERCASE][/B]</label>
                    </control>
                </focusedlayout>
            </control>

            <control type="scrollbar" id="152">
                <hitrect x="1088" y="33" w="110" h="874" />
                <left>1128</left>
                <top>33</top>
                <width>10</width>
                <height>{{ vscale(874) }}</height>
                <onleft>101</onleft>
                <visible>true</visible>
                <texturesliderbackground colordiffuse="40000000" border="5">script.plex/white-square-rounded.png</texturesliderbackground>
                <texturesliderbar colordiffuse="77FFFFFF" border="5">script.plex/white-square-rounded.png</texturesliderbar>
                <texturesliderbarfocus colordiffuse="FFE5A00D" border="5">script.plex/white-square-rounded.png</texturesliderbarfocus>
                <textureslidernib>-</textureslidernib>
                <textureslidernibfocus>-</textureslidernibfocus>
                <pulseonselect>false</pulseonselect>
                <orientation>vertical</orientation>
                <showonepage>false</showonepage>
                <onleft>151</onleft>
            </control>
        </control>
    </control>
{% endblock content %}