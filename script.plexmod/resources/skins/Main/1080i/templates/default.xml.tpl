{% extends "base.xml.tpl" %}{# this extends base and adds background and default header blocks #}
{% block controls %}
    {% block background %}
        {% include "includes/default_background.xml.tpl" %}
    {% endblock %}
    <!-- block content -->
    {% block content %}{% endblock %}

    {% block header %}
    <control type="group" id="200">
        {% block header_anim %}<animation effect="slide" end="0,{{ vscale(-300) }}" time="200" tween="quadratic" easing="out" condition="!String.IsEmpty(Window.Property(on.extras)) + !ControlGroup(200).HasFocus(0)">Conditional</animation>{% endblock %}
        <defaultcontrol always="true">201</defaultcontrol>
        <posx>0</posx>
        <posy>0</posy>
        <width>1920</width>
        <height>{{ vscale(135) }}</height>
        {% block header_bgfade %}
        <control type="image">
            <animation effect="fade" start="0" end="100" time="200" tween="quadratic" easing="out" reversible="true">VisibleChange</animation>
            <visible>ControlGroup(200).HasFocus(0) + !String.IsEmpty(Window.Property(on.extras))</visible>
            <posx>0</posx>
            <posy>0</posy>
            <width>1920</width>
            <height>{{ vscale(135) }}</height>
            <texture>script.plex/white-square.png</texture>
            <colordiffuse>C0000000</colordiffuse>
        </control>
        {% endblock %}
        <control type="grouplist">
            <posx>60</posx>
            <posy>{{ vscale(47.5) }}</posy>
            <width>1000</width>
            <height>{{ vscale(40) }}</height>
            <align>left</align>
            <itemgap>60</itemgap>
            <orientation>horizontal</orientation>
            <ondown>50</ondown>
            <control type="group">
                <width>40</width>
                <height>{{ vscale(40) }}</height>
                <control type="button" id="201">
                    <animation effect="zoom" start="100" end="144" time="100" center="20,{{ vscale(20) }}" reversible="false">Focus</animation>
                    <animation effect="zoom" start="144" end="100" time="100" center="20,{{ vscale(20) }}" reversible="false">UnFocus</animation>
                    <width>40</width>
                    <height>{{ vscale(40) }}</height>
                    <onright>202</onright>
                    <ondown>50</ondown>
                    <font>font12</font>
                    <focusedcolor>FF000000</focusedcolor>
                    <texturefocus colordiffuse="FFE5A00D">script.plex/buttons/home-focus.png</texturefocus>
                    <texturenofocus colordiffuse="99FFFFFF">script.plex/buttons/home.png</texturenofocus>
                    <label> </label>
                </control>
            </control>
            {% block topleft_add %}{% endblock %}
            <control type="group">
                <width>40</width>
                <height>{{ vscale(40) }}</height>
                <control type="button" id="202">
                    <animation effect="zoom" start="100" end="144" time="100" center="20,{{ vscale(20) }}" reversible="false">Focus</animation>
                    <animation effect="zoom" start="144" end="100" time="100" center="20,{{ vscale(20) }}" reversible="false">UnFocus</animation>
                    <width>40</width>
                    <height>{{ vscale(40) }}</height>
                    <onright>204</onright>
                    <onleft>201</onleft>
                    <ondown>50</ondown>
                    <font>font12</font>
                    <focusedcolor>FF000000</focusedcolor>
                    <texturefocus colordiffuse="FFE5A00D">script.plex/buttons/search-focus.png</texturefocus>
                    <texturenofocus colordiffuse="99FFFFFF">script.plex/buttons/search.png</texturenofocus>
                    <label> </label>
                </control>
            </control>
        </control>
        <control type="group">
            <visible>Player.HasAudio + String.IsEmpty(Window(10000).Property(script.plex.theme_playing))</visible>
            <posx>438</posx>
            <posy>0</posy>
            <control type="button" id="204">
                <visible>Player.HasAudio + String.IsEmpty(Window(10000).Property(script.plex.theme_playing))</visible>
                <posx>-10</posx>
                <posy>{{ vscale(38) }}</posy>
                <width>260</width>
                <height>{{ vscale(75) }}</height>
                <onleft>202</onleft>
                <ondown>50</ondown>
                <font>font12</font>
                <textcolor>FFFFFFFF</textcolor>
                <focusedcolor>FF000000</focusedcolor>
                <align>right</align>
                <aligny>center</aligny>
                <texturefocus colordiffuse="FFE5A00D" border="10">script.plex/white-square-rounded.png</texturefocus>
                <texturenofocus>-</texturenofocus>
                <textoffsetx>100</textoffsetx>
                <textoffsety>0</textoffsety>
                <label> </label>
            </control>
            <control type="image">
                <posx>0</posx>
                <posy>{{ vscale(48) }}</posy>
                <width>42</width>
                <height>{{ vscale(42) }}</height>
                <texture>$INFO[Player.Art(thumb)]</texture>
            </control>

            <control type="group">
                <visible>!Control.HasFocus(204)</visible>
                <control type="label">
                    <posx>53</posx>
                    <posy>{{ vscale(48) }}</posy>
                    <width>187</width>
                    <height>{{ vscale(20) }}</height>
                    <font>font10</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <info>MusicPlayer.Artist</info>
                </control>
                <control type="label">
                    <posx>53</posx>
                    <posy>{{ vscale(72) }}</posy>
                    <width>187</width>
                    <height>{{ vscale(20) }}</height>
                    <font>font10</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>FFFFFFFF</textcolor>
                    <info>MusicPlayer.Title</info>
                </control>
            </control>
            <control type="group">
                <visible>Control.HasFocus(204)</visible>
                <control type="label">
                    <posx>53</posx>
                    <posy>{{ vscale(48) }}</posy>
                    <width>187</width>
                    <height>{{ vscale(20) }}</height>
                    <font>font10</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>FF000000</textcolor>
                    <info>MusicPlayer.Artist</info>
                </control>
                <control type="label">
                    <posx>53</posx>
                    <posy>{{ vscale(72) }}</posy>
                    <width>187</width>
                    <height>{{ vscale(20) }}</height>
                    <font>font10</font>
                    <align>left</align>
                    <aligny>center</aligny>
                    <textcolor>FF000000</textcolor>
                    <info>MusicPlayer.Title</info>
                </control>
            </control>

            <control type="progress">
                <description>Progressbar</description>
                <posx>0</posx>
                <posy>{{ vscale(102) }}</posy>
                <width>240</width>
                <height>{{ vscale(1) }}</height>
                <texturebg colordiffuse="9AFFFFFF">script.plex/white-square-1px.png</texturebg>
                <lefttexture>-</lefttexture>
                <midtexture colordiffuse="FFCC7B19">script.plex/white-square-1px.png</midtexture>
                <righttexture>-</righttexture>
                <overlaytexture>-</overlaytexture>
                <info>Player.Progress</info>
            </control>
        </control>
        <control type="label">
            <right>213</right>
            <posy>{{ vscale(35) }}</posy>
            <width>200</width>
            <height>{{ vscale(65) }}</height>
            <font>font12</font>
            <align>right</align>
            <aligny>center</aligny>
            <textcolor>FFFFFFFF</textcolor>
            <label>$INFO[System.Time]</label>
        </control>
        <control type="image">
            <posx>153r</posx>
            <posy>{{ vscale(47.5) }}</posy>
            <width>93</width>
            <height>{{ vscale(43) }}</height>
            <texture>script.plex/home/plex.png</texture>
        </control>
    </control>

    <control type="group">
        <visible>!String.IsEmpty(Window.Property(search.dialog))</visible>
        <control type="group" >
            <visible>!String.IsEmpty(Window.Property(search.dialog.hasresults))</visible>
            <control type="image">
                <posx>0</posx>
                <posy>0</posy>
                <width>1920</width>
                <height>1080</height>
                <texture>script.plex/home/background-fallback.png</texture>
                {% include "includes/scale_background.xml.tpl" %}
            </control>
            <control type="image">
                <posx>0</posx>
                <posy>0</posy>
                <width>1920</width>
                <height>1080</height>
                <texture background="true">$INFO[Window.Property(background)]</texture>
                {% include "includes/scale_background.xml.tpl" %}
            </control>
        </control>
        <control type="image">
            <posx>0</posx>
            <posy>0</posy>
            <width>1920</width>
            <height>1080</height>
            <texture colordiffuse="99606060">script.plex/white-square.png</texture>
        </control>
    </control>
    {% endblock header %}
{% endblock controls %}