{% extends "base.xml.tpl" %}
{% block headers %}<defaultcontrol>100</defaultcontrol>{% endblock %}
{% block controls %}
<control type="image">
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>1080</height>
    <texture>script.plex/sign_in/refresh-code.jpg</texture>
</control>

<control type="button" id="100">
    <posx>1383</posx>
    <posy>{{ vscale(802) }}</posy>
    <width>335</width>
    <height>{{ vscale(102) }}</height>
    <onup>200</onup>
    <font>font13</font>
    <textcolor>FFFFFFFF</textcolor>
    <focusedcolor>FFFFFFFF</focusedcolor>
    <align>center</align>
    <aligny>center</aligny>
    <texturefocus>-</texturefocus>
    <texturenofocus>-</texturenofocus>
    <textoffsetx>0</textoffsetx>
    <textoffsety>0</textoffsety>
    <label> </label>
</control>
{% endblock controls %}