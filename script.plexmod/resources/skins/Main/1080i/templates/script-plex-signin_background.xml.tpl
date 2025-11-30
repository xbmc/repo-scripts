{% extends "base.xml.tpl" %}
{% block headers %}<defaultcontrol>100</defaultcontrol>{% endblock %}
{% block controls %}
<control type="image">
    <posx>0</posx>
    <posy>0</posy>
    <width>1920</width>
    <height>1080</height>
    <texture background="true">script.plex/home/background-fallback_black.png</texture>
</control>
<control type="image">
    <posx>0</posx>
    <posy>{% if core.needs_scaling %}{{ vperc(vscale(1080)) }}{% else %}0{% endif %}</posy>
    <width>1920</width>
    <height>{{ vscale(1080) }}</height>
    <texture>script.plex/sign_in/back.jpg</texture>
</control>
{% endblock %}