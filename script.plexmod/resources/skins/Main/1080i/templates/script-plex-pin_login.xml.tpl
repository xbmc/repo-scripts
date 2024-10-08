{% extends "base.xml.tpl" %}
{% block controls %}
<control type="image">
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>1080</height>
    <texture background="true">script.plex/home/background-fallback_black.png</texture>
</control>
<control type="image">
    <visible>!String.IsEmpty(Window.Property(pin.image.0))</visible>
    <posx>0</posx>
    <posy>{% if core.needs_scaling %}{{ vperc(vscale(1080)) }}{% else %}0{% endif %}</posy>
    <width>1920</width>
    <height>{{ vscale(1080) }}</height>
    <texture>script.plex/sign_in/pin-display.jpg</texture>
</control>
<control type="image">
    <visible>String.IsEmpty(Window.Property(pin.image.0)) + String.IsEmpty(Window.Property(linking))</visible>
    <posx>0</posx>
    <posy>{% if core.needs_scaling %}{{ vperc(vscale(1080)) }}{% else %}0{% endif %}</posy>
    <width>1920</width>
    <height>{{ vscale(1080) }}</height>
    <texture>script.plex/sign_in/generating-code.jpg</texture>
</control>
<control type="image">
    <visible>!String.IsEmpty(Window.Property(linking))</visible>
    <posx>0</posx>
    <posy>{% if core.needs_scaling %}{{ vperc(vscale(1080)) }}{% else %}0{% endif %}</posy>
    <width>1920</width>
    <height>{{ vscale(1080) }}</height>
    <texture>script.plex/sign_in/linking-account.jpg</texture>
</control>

<control type="label">
    <posx>270</posx>
    <posy>{{ vscale(738) }}</posy>
    <width>800</width>
    <height>{{ vscale(153) }}</height>
    <font>WeatherTemp</font>
    <align>left</align>
    <aligny>center</aligny>
    <textcolor>FFFFFFFF</textcolor>
    <label>$INFO[Window.Property(pin)]</label>
</control>

<control type="grouplist" id="400">
    <defaultcontrol>406</defaultcontrol>
    <posx>265</posx>
    <posy>{{ vscale(708) }}</posy>
    <width>1000</width>

    <height>{{ vscale(200) }}</height>
    <align>left</align>
    <itemgap>0</itemgap>
    <orientation>horizontal</orientation>
    <control type="image">
        <width>200</width>
        <height>{{ vscale(200) }}</height>
        <texture>$INFO[Window.Property(pin.image.0)]</texture>
    </control>
    <control type="image">
        <width>200</width>
        <height>{{ vscale(200) }}</height>
        <texture>$INFO[Window.Property(pin.image.1)]</texture>
    </control>
    <control type="image">
        <width>200</width>
        <height>{{ vscale(200) }}</height>
        <texture>$INFO[Window.Property(pin.image.2)]</texture>
    </control>
    <control type="image">
        <width>200</width>
        <height>{{ vscale(200) }}</height>
        <texture>$INFO[Window.Property(pin.image.3)]</texture>
    </control>

</control>
{% endblock controls %}