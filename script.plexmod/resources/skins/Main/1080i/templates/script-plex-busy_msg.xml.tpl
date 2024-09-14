{% extends "base.xml.tpl" %}
{% block backgroundcolor %}{% endblock %}
{% block controls %}
<control type="group">
    <posx>0</posx>
    <posy>0</posy>
    <animation effect="fade" start="0" end="100">WindowOpen</animation>
    <control type="image">
        <posx>840</posx>
        <posy>{{ vperc(vscale(150)) }}</posy>
        <width>240</width>
        <height>{{ vscale(150) }}</height>
        <texture>script.plex/busy-back.png</texture>
        <colordiffuse>A0FFFFFF</colordiffuse>
    </control>
    <control type="label">
        <posx>840</posx>
        <posy>{{ vperc(vscale(150)) }}</posy>
        <width>240</width>
        <height>{{ vscale(150) }}</height>
        <align>center</align>
        <aligny>center</aligny>
        <textcolor>FFFFFFFF</textcolor>
        <label>$INFO[Window.Property(message)]</label>
        <font>font14</font>
        <shadowcolor>black</shadowcolor>
    </control>
</control>
{% endblock controls %}