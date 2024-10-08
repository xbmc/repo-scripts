{% extends "default.xml.tpl" %}
{% block headers %}<defaultcontrol>152</defaultcontrol>{% endblock %}

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
    <posy>{{ vscale(135) }}</posy>

    <control type="group">
        <posx>60</posx>
        <posy>0</posy>
        <control type="group">
            <visible>!String.IsEmpty(Window.Property(is.poster))</visible>
            <control type="image">
                <posx>0</posx>
                <posy>0</posy>
                <width>519</width>
                <height>{{ vscale(769) }}</height>
                <texture>$INFO[Window.Property(thumb.fallback)]</texture>
                <aspectratio aligny="top">scale</aspectratio>
            </control>
            <control type="image">
                <posx>0</posx>
                <posy>0</posy>
                <width>519</width>
                <height>{{ vscale(769) }}</height>
                <texture>$INFO[Window.Property(thumb)]</texture>
                <aspectratio aligny="top">scale</aspectratio>
            </control>
        </control>
        <control type="group">
            <visible>!String.IsEmpty(Window.Property(is.square))</visible>
            <control type="image">
                <posx>0</posx>
                <posy>0</posy>
                <width>519</width>
                <height>{{ vscale(519) }}</height>
                <texture>$INFO[Window.Property(thumb.fallback)]</texture>
                <aspectratio aligny="top">keep</aspectratio>
            </control>
            <control type="image">
                <posx>0</posx>
                <posy>0</posy>
                <width>519</width>
                <height>{{ vscale(519) }}</height>
                <texture>$INFO[Window.Property(thumb)]</texture>
                <aspectratio aligny="top">scale</aspectratio>
            </control>
        </control>
        <control type="group">
            <visible>!String.IsEmpty(Window.Property(is.16x9))</visible>
            <control type="image">
                <posx>0</posx>
                <posy>0</posy>
                <width>519</width>
                <height>{{ vscale(292) }}</height>
                <texture>$INFO[Window.Property(thumb.fallback)]</texture>
                <aspectratio>scale</aspectratio>
            </control>
            <control type="image">
                <posx>0</posx>
                <posy>0</posy>
                <width>519</width>
                <height>{{ vscale(292) }}</height>
                <texture>$INFO[Window.Property(thumb)]</texture>
                <aspectratio aligny="top">scale</aspectratio>
            </control>
        </control>
        <control type="label">
            <posx>579</posx>
            <posy>5</posy>
            <width>1190</width>
            <height>{{ vscale(40) }}</height>
            <font>font13</font>
            <align>left</align>
            <aligny>center</aligny>
            <textcolor>FFFFFFFF</textcolor>
            <label>$INFO[Window.Property(title.main)]</label>
        </control>
        <control type="label">
            <posx>579</posx>
            <posy>{{ vscale(55) }}</posy>
            <width>1190</width>
            <height>{{ vscale(40) }}</height>
            <font>font13</font>
            <align>left</align>
            <aligny>center</aligny>
            <textcolor>FFDDDDDD</textcolor>
            <label>$INFO[Window.Property(title.sub)]</label>
        </control>
        <control type="textbox">
            <posx>579</posx>
            <posy>{{ vscale(157) }}</posy>
            <pagecontrol>152</pagecontrol>
            <width>1190</width>
            <height>{{ vscale(718) }}</height>
            <font>font13</font>
            <align>left</align>
            <textcolor>FFDDDDDD</textcolor>
            <label>$INFO[Window.Property(info)]</label>
        </control>
        <control type="scrollbar" id="152">
            <hitrect x="1754" y="157" w="126" h="718" />
            <left>1794</left>
            <top>157</top>
            <width>6</width>
            <height>{{ vscale(718) }}</height>
            <visible>true</visible>
            <texturesliderbackground colordiffuse="40000000" border="5">script.plex/white-square.png</texturesliderbackground>
            <texturesliderbar colordiffuse="77FFFFFF" border="5">script.plex/white-square.png</texturesliderbar>
            <texturesliderbarfocus colordiffuse="FFE5A00D" border="5">script.plex/white-square.png</texturesliderbarfocus>
            <textureslidernib>-</textureslidernib>
            <textureslidernibfocus>-</textureslidernibfocus>
            <pulseonselect>false</pulseonselect>
            <orientation>vertical</orientation>
            <showonepage>false</showonepage>
            <onleft>204</onleft>
        </control>
    </control>
</control>
{% endblock content %}