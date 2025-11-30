{% extends "default.xml.tpl" %}
{% block headers %}<defaultcontrol>100</defaultcontrol>{% endblock %}
{% block header_bgfade %}{% endblock %}
{% block topleft_add %}
<control type="label">
    <width max="500">auto</width>
    <height>{{ vscale(40) }}</height>
    <font>font12</font>
    <align>left</align>
    <aligny>center</aligny>
    <textcolor>FFFFFFFF</textcolor>
    <label>[UPPERCASE]$ADDON[script.plexmod 32333][/UPPERCASE]</label>
</control>
{% endblock %}
{% block content %}
<control type="group">
    <visible>String.IsEmpty(Window.Property(use_solid_background))</visible>
    <control type="image">
        <visible>String.IsEmpty(Window.Property(use_bg_fallback))</visible>
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>1080</height>
        <texture background="true">script.plex/home/background-fallback_black.png</texture>
    </control>
    <control type="image">
        <visible>!String.IsEmpty(Window.Property(use_bg_fallback))</visible>
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>1080</height>
        <texture background="true">script.plex/home/background-fallback.png</texture>
    </control>
    <control type="image">
        <visible>String.IsEmpty(Window.Property(use_bg_fallback))</visible>
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>1080</height>
        <texture background="true" fallback="script.plex/home/background-fallback_black.png">$INFO[Window.Property(background_static)]</texture>
    </control>
    <control type="image">
        <visible>String.IsEmpty(Window.Property(use_bg_fallback))</visible>
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>1080</height>
        <fadetime>1000</fadetime>
        <texture background="true">$INFO[Window.Property(background)]</texture>
    </control>
</control>

<control type="group" id="50">
    <posx>0</posx>
    <posy>{{ vscale(115) }}</posy>
    <defaultcontrol always="true">101</defaultcontrol>

    <control type="group" id="100">
        <visible>Integer.IsGreater(Container(101).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
        <defaultcontrol>101</defaultcontrol>
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>{{ vscale(360) }}</height>
        <control type="label">
            <posx>60</posx>
            <posy>0</posy>
            <width>1800</width>
            <height>{{ vscale(80) }}</height>
            <font>font12</font>
            <align>left</align>
            <aligny>center</aligny>
            <textcolor>FFFFFFFF</textcolor>
            <label>[UPPERCASE]$ADDON[script.plexmod 32048][/UPPERCASE]</label>
        </control>
        <control type="list" id="101">
            <posx>0</posx>
            <posy>{{ vscale(30) }}</posy>
            <width>1920</width>
            <height>{{ vscale(390) }}</height>
            <onup>200</onup>
            <ondown>301</ondown>
            <scrolltime>200</scrolltime>
            <orientation>horizontal</orientation>
            <preloaditems>2</preloaditems>
            <!-- ITEM LAYOUT ########################################## -->
            <itemlayout width="298">
                <control type="group">
                    <posx>40</posx>
                    <posy>{{ vscale(40) }}</posy>
                    <control type="group">
                        <posx>21</posx>
                        <posy>{{ vscale(21) }}</posy>
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>238</width>
                            <height>{{ vscale(238) }}</height>
                            <texture>$INFO[ListItem.Property(thumb.fallback)]</texture>
                            <aspectratio>scale</aspectratio>
                        </control>
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>238</width>
                            <height>{{ vscale(238) }}</height>
                            <texture background="true">$INFO[ListItem.Thumb]</texture>
                            <aspectratio>scale</aspectratio>
                        </control>
                        <control type="label">
                            <posx>-30</posx>
                            <posy>{{ vscale(248) }}</posy>
                            <width>298</width>
                            <height>{{ vscale(40) }}</height>
                            <font>font10</font>
                            <align>center</align>
                            <textcolor>FFFFFFFF</textcolor>
                            <label>$INFO[ListItem.Label]</label>
                        </control>
                        <control type="label">
                            <posx>-30</posx>
                            <posy>{{ vscale(278) }}</posy>
                            <width>298</width>
                            <height>{{ vscale(40) }}</height>
                            <font>font10</font>
                            <align>center</align>
                            <textcolor>FFFFFFFF</textcolor>
                            <label>$INFO[ListItem.Label2]</label>
                        </control>
                    </control>
                </control>
            </itemlayout>

            <!-- FOCUSED LAYOUT ####################################### -->
            <focusedlayout width="298">
                <control type="group">
                    <posx>40</posx>
                    <posy>{{ vscale(40) }}</posy>
                    <control type="group">
                        <animation effect="zoom" start="100" end="116" time="100" center="140,{{ vscale(140) }}" reversible="false">Focus</animation>
                        <animation effect="zoom" start="116" end="100" time="100" center="140,{{ vscale(140) }}" reversible="false">UnFocus</animation>
                        <posx>0</posx>
                        <posy>0</posy>
                        <control type="image">
                            <visible>Control.HasFocus(101)</visible>
                            <posx>-19</posx>
                            <posy>{{ vscale(-19) }}</posy>
                            <width>318</width>
                            <height>{{ vscale(318) }}</height>
                            <texture border="42">script.plex/drop-shadow.png</texture>
                        </control>
                        <control type="group">
                            <posx>21</posx>
                            <posy>{{ vscale(21) }}</posy>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>238</width>
                                <height>{{ vscale(238) }}</height>
                                <texture>$INFO[ListItem.Property(thumb.fallback)]</texture>
                                <aspectratio>scale</aspectratio>
                            </control>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>238</width>
                                <height>{{ vscale(238) }}</height>
                                <texture background="true">$INFO[ListItem.Thumb]</texture>
                                <aspectratio>scale</aspectratio>
                            </control>
                            <control type="label">
                                <posx>-30</posx>
                                <posy>{{ vscale(248) }}</posy>
                                <width>298</width>
                                <height>{{ vscale(40) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <textcolor>FFFFFFFF</textcolor>
                                <label>$INFO[ListItem.Label]</label>
                            </control>
                            <control type="label">
                                <posx>-30</posx>
                                <posy>{{ vscale(278) }}</posy>
                                <width>298</width>
                                <height>{{ vscale(40) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <textcolor>FFFFFFFF</textcolor>
                                <label>$INFO[ListItem.Label2]</label>
                            </control>
                        </control>
                        <control type="image">
                            <visible>Control.HasFocus(101)</visible>
                            <posx>16</posx>
                            <posy>{{ vscale(16) }}</posy>
                            <width>248</width>
                            <height>{{ vscale(248) }}</height>
                            <texture border="10">script.plex/home/selected.png</texture>
                        </control>
                    </control>
                </control>
            </focusedlayout>
        </control>
    </control>

    <control type="group" id="300">
        <visible>Integer.IsGreater(Container(301).NumItems,0) + String.IsEmpty(Window.Property(drawing))</visible>
        <animation effect="slide" end="0,{{ vscale(-420) }}" condition="!Control.IsVisible(100)">Conditional</animation>
        <defaultcontrol>301</defaultcontrol>
        <posx>0</posx>
        <posy>{{ vscale(445) }}</posy>
        <width>1920</width>
        <height>{{ vscale(360) }}</height>
        <control type="image">
            <visible>Control.IsVisible(100)</visible>
            <posx>60</posx>
            <posy>0</posy>
            <width>1800</width>
            <height>{{ vscale(2) }}</height>
            <texture>script.plex/white-square.png</texture>
            <colordiffuse>661F1F1F</colordiffuse>
        </control>
        <control type="label">
            <posx>60</posx>
            <posy>0</posy>
            <width>1800</width>
            <height>{{ vscale(80) }}</height>
            <font>font12</font>
            <align>left</align>
            <aligny>center</aligny>
            <textcolor>FFFFFFFF</textcolor>
            <label>[UPPERCASE]$ADDON[script.plexmod 32053][/UPPERCASE]</label>
        </control>
        <control type="list" id="301">
            <posx>-21.5</posx>
            <posy>{{ vscale(30) }}</posy>
            <width>1941.5</width>
            <height>{{ vscale(700) }}</height>
            <onup>101</onup>
            <scrolltime>200</scrolltime>
            <orientation>horizontal</orientation>
            <preloaditems>2</preloaditems>
            <!-- ITEM LAYOUT ########################################## -->
            <itemlayout width="602">
                <control type="group">
                    <posx>40</posx>
                    <posy>{{ vscale(40) }}</posy>
                    <control type="group">
                        <posx>41.5</posx>
                        <posy>{{ vscale(25.5) }}</posy>
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>537</width>
                            <height>{{ vscale(303) }}</height>
                            <texture>$INFO[ListItem.Property(thumb.fallback)]</texture>
                            <aspectratio>scale</aspectratio>
                        </control>
                        <control type="image">
                            <posx>0</posx>
                            <posy>0</posy>
                            <width>537</width>
                            <height>{{ vscale(303) }}</height>
                            <texture background="true">$INFO[ListItem.Thumb]</texture>
                            <aspectratio>scale</aspectratio>
                        </control>
                        <control type="label">
                            <posx>-30</posx>
                            <posy>{{ vscale(313) }}</posy>
                            <width>597</width>
                            <height>{{ vscale(40) }}</height>
                            <font>font10</font>
                            <align>center</align>
                            <textcolor>FFFFFFFF</textcolor>
                            <label>$INFO[ListItem.Label]</label>
                        </control>
                        <control type="label">
                            <posx>-30</posx>
                            <posy>{{ vscale(343) }}</posy>
                            <width>597</width>
                            <height>{{ vscale(40) }}</height>
                            <font>font10</font>
                            <align>center</align>
                            <textcolor>FFFFFFFF</textcolor>
                            <label>$INFO[ListItem.Label2]</label>
                        </control>
                    </control>
                </control>
            </itemlayout>

            <!-- FOCUSED LAYOUT ####################################### -->
            <focusedlayout width="602">
                <control type="group">
                    <posx>40</posx>
                    <posy>{{ vscale(40) }}</posy>
                    <control type="group">
                        <animation effect="zoom" start="100" end="110" time="100" center="310,{{ vscale(177) }}" reversible="false">Focus</animation>
                        <animation effect="zoom" start="110" end="100" time="100" center="310,{{ vscale(177) }}" reversible="false">UnFocus</animation>
                        <posx>0</posx>
                        <posy>0</posy>
                        <control type="image">
                            <visible>Control.HasFocus(301)</visible>
                            <posx>1.5</posx>
                            <posy>{{ vscale(-15.5) }}</posy>
                            <width>617</width>
                            <height>{{ vscale(383) }}</height>
                            <texture border="42">script.plex/drop-shadow.png</texture>
                        </control>
                        <control type="group">
                            <posx>41.5</posx>
                            <posy>{{ vscale(25.5) }}</posy>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>537</width>
                                <height>{{ vscale(303) }}</height>
                                <texture>$INFO[ListItem.Property(thumb.fallback)]</texture>
                                <aspectratio>scale</aspectratio>
                            </control>
                            <control type="image">
                                <posx>0</posx>
                                <posy>0</posy>
                                <width>537</width>
                                <height>{{ vscale(303) }}</height>
                                <texture background="true">$INFO[ListItem.Thumb]</texture>
                                <aspectratio>scale</aspectratio>
                            </control>
                            <control type="label">
                                <posx>-30</posx>
                                <posy>{{ vscale(313) }}</posy>
                                <width>597</width>
                                <height>{{ vscale(40) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <textcolor>FFFFFFFF</textcolor>
                                <label>$INFO[ListItem.Label]</label>
                            </control>
                            <control type="label">
                                <posx>-30</posx>
                                <posy>{{ vscale(343) }}</posy>
                                <width>597</width>
                                <height>{{ vscale(40) }}</height>
                                <font>font10</font>
                                <align>center</align>
                                <textcolor>FFFFFFFF</textcolor>
                                <label>$INFO[ListItem.Label2]</label>
                            </control>
                        </control>
                        <control type="image">
                            <visible>Control.HasFocus(301)</visible>
                            <posx>36.5</posx>
                            <posy>{{ vscale(20.5) }}</posy>
                            <width>547</width>
                            <height>{{ vscale(313) }}</height>
                            <texture border="10">script.plex/home/selected.png</texture>
                        </control>
                    </control>
                </control>
            </focusedlayout>
        </control>
    </control>
</control>
{% endblock content %}