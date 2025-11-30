{% extends "base.xml.tpl" %}
{% block headers %}{% endblock %}
{% block backgroundcolor %}<backgroundcolor>0xff111111</backgroundcolor>{% endblock %}

{% block controls %}
<control type="image">
    <visible>!String.IsEmpty(Window(10000).Property(script.plex.background.splash))</visible>
    <posx>710</posx>
    <posy>{{ vperc(vscale(232.5)) }}</posy>
    <width>500</width>
    <height>{{ vscale(232.5) }}</height>
    <texture>script.plex/splash.png</texture>
</control>

<control type="group">
    <visible>!String.IsEmpty(Window(10000).Property(script.plex.background.busy))</visible>
    <control type="image">
        <posx>812</posx>
        <posy>{{ vperc(vscale(139)) }}</posy>
        <width>300</width>
        <height>{{ vscale(139) }}</height>
        <texture>script.plex/user_select/plex.png</texture>
    </control>
    <control type="image">
        <posx>840</posx>
        <posy>{{ vperc(vscale(150)) }}</posy>
        <width>240</width>
        <height>{{ vscale(150) }}</height>
        <texture>script.plex/busy-back.png</texture>
        <colordiffuse>A0FFFFFF</colordiffuse>
    </control>
    <control type="image">
        <posx>915</posx>
        <posy>{{ vperc(vscale(38)) }}</posy>
        <width>90</width>
        <height>{{ vscale(38) }}</height>
        <texture diffuse="script.plex/busy-diffuse.png">script.plex/busy.gif</texture>
    </control>
</control>

<control type="group">
    <visible>!String.IsEmpty(Window(10000).Property(script.plex.background.shutdown))</visible>
    <control type="image">
        <posx>840</posx>
        <posy>{{ vperc(vscale(150)) }}</posy>
        <width>240</width>
        <height>{{ vscale(150) }}</height>
        <texture>script.plex/busy-back.png</texture>
        <colordiffuse>A0FFFFFF</colordiffuse>
    </control>
    <control type="image">
        <posx>915</posx>
        <posy>{{ vperc(vscale(38)) }}</posy>
        <width>90</width>
        <height>{{ vscale(38) }}</height>
        <texture diffuse="script.plex/busy-diffuse.png">script.plex/busy.gif</texture>
    </control>
</control>
{% endblock controls %}