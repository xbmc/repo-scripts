<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<window>{# this is the basic window/dialog structure #}
    {% block headers %}{% endblock %}
    {% block coordinates %}
    <coordinates>
        <system>1</system>
        <posx>0</posx>
        <posy>0</posy>
    </coordinates>
    {% endblock coordinates %}
    {% block backgroundcolor %}<backgroundcolor>$INFO[Window.Property(background_colour)]</backgroundcolor>{% endblock %}
    <controls>
        {% block controls %}{% endblock %}
        <control type="label" id="666"><visible>false</visible></control><!-- sanity check dummy -->
    </controls>
</window>
