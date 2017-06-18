import gettext
import re
import pycountries
import pycountries.db
import pytest


@pytest.fixture(autouse=True, scope='session')
def logging():
    import logging
    logging.basicConfig(level=logging.DEBUG)


def test_country_list():
    assert len(pycountries.countries) == 249
    assert isinstance(list(pycountries.countries)[0], pycountries.db.Data)


def test_germany_has_all_attributes():
    germany = pycountries.countries.get(alpha_2='DE')
    assert germany.alpha_2 == u'DE'
    assert germany.alpha_3 == u'DEU'
    assert germany.numeric == u'276'
    assert germany.name == u'Germany'
    assert germany.official_name == u'Federal Republic of Germany'


def test_subdivisions_directly_accessible():
    assert len(pycountries.subdivisions) == 4835
    assert isinstance(list(pycountries.subdivisions)[0], pycountries.db.Data)

    de_st = pycountries.subdivisions.get(code='DE-ST')
    assert de_st.code == u'DE-ST'
    assert de_st.name == u'Sachsen-Anhalt'
    assert de_st.type == u'State'
    assert de_st.parent is None
    assert de_st.parent_code is None
    assert de_st.country is pycountries.countries.get(alpha_2='DE')


def test_subdivisions_have_subdivision_as_parent():
    al_br = pycountries.subdivisions.get(code='AL-BU')
    assert al_br.code == u'AL-BU'
    assert al_br.name == u'Bulqiz\xeb'
    assert al_br.type == u'District'
    assert al_br.parent_code == u'AL-09'
    assert al_br.parent is pycountries.subdivisions.get(code='AL-09')
    assert al_br.parent.name == u'Dib\xebr'


def test_query_subdivisions_of_country():
    assert len(pycountries.subdivisions.get(country_code='DE')) == 16
    assert len(pycountries.subdivisions.get(country_code='US')) == 57


def test_scripts():
    assert len(pycountries.scripts) == 182
    assert isinstance(list(pycountries.scripts)[0], pycountries.db.Data)

    latin = pycountries.scripts.get(name='Latin')
    assert latin.alpha_4 == u'Latn'
    assert latin.name == u'Latin'
    assert latin.numeric == u'215'


def test_currencies():
    assert len(pycountries.currencies) == 170
    assert isinstance(list(pycountries.currencies)[0], pycountries.db.Data)

    argentine_peso = pycountries.currencies.get(alpha_3='ARS')
    assert argentine_peso.alpha_3 == u'ARS'
    assert argentine_peso.name == u'Argentine Peso'
    assert argentine_peso.numeric == u'032'


def test_languages():
    assert len(pycountries.languages) == 7847
    assert isinstance(list(pycountries.languages)[0], pycountries.db.Data)

    aragonese = pycountries.languages.get(alpha_2='an')
    assert aragonese.alpha_2 == u'an'
    assert aragonese.alpha_3 == u'arg'
    assert aragonese.name == u'Aragonese'

    bengali = pycountries.languages.get(alpha_2='bn')
    assert bengali.name == u'Bengali'
    assert bengali.common_name == u'Bangla'


def test_locales():
    german = gettext.translation(
        'iso3166', pycountries.LOCALES_DIR, languages=['de'])
    german.install()
    assert __builtins__['_']('Germany') == 'Deutschland'


def test_removed_countries():
    ussr = pycountries.historic_countries.get(alpha_3='SUN')
    assert isinstance(ussr, pycountries.db.Data)
    assert ussr.alpha_4 == u'SUHH'
    assert ussr.alpha_3 == u'SUN'
    assert ussr.name == u'USSR, Union of Soviet Socialist Republics'
    assert ussr.withdrawal_date == u'1992-08-30'


def test_repr():
    assert re.match("Country\\(alpha_2=u?'DE', "
                    "alpha_3=u?'DEU', "
                    "name=u?'Germany', "
                    "numeric=u?'276', "
                    "official_name=u?'Federal Republic of Germany'\\)",
                    repr(pycountries.countries.get(alpha_2='DE')))


def test_dir():
    germany = pycountries.countries.get(alpha_2='DE')
    for n in 'alpha_2', 'alpha_3', 'name', 'numeric', 'official_name':
        assert n in dir(germany)


def test_get():
    c = pycountries.countries
    with pytest.raises(TypeError):
        c.get(alpha_2='DE', alpha_3='DEU')
    assert c.get(alpha_2='DE') == c.get(alpha_3='DEU')


def test_lookup():
    c = pycountries.countries
    g = c.get(alpha_2='DE')
    assert g == c.lookup('de')
    assert g == c.lookup('DEU')
    assert g == c.lookup('276')
    assert g == c.lookup('germany')
    assert g == c.lookup('Federal Republic of Germany')
    # try a generated field
    bqaq = pycountries.historic_countries.get(alpha_4='BQAQ')
    assert bqaq == pycountries.historic_countries.lookup('atb')
    german = pycountries.languages.get(alpha_2='de')
    assert german == pycountries.languages.lookup('De')
    euro = pycountries.currencies.get(alpha_3='EUR')
    assert euro == pycountries.currencies.lookup('euro')
    latin = pycountries.scripts.get(name='Latin')
    assert latin == pycountries.scripts.lookup('latn')
    al_bu = pycountries.subdivisions.get(code='AL-BU')
    assert al_bu == pycountries.subdivisions.lookup('al-bu')
    with pytest.raises(LookupError):
        pycountries.countries.lookup('bogus country')
    with pytest.raises(LookupError):
        pycountries.countries.lookup(12345)


def test_subdivision_parent():
    s = pycountries.subdivisions
    sd = s.get(code='CV-BV')
    assert sd.parent_code == 'CV-B'
    assert sd.parent is s.get(code=sd.parent_code)


def test_subdivision_empty_list():
    s = pycountries.subdivisions
    assert len(s.get(country_code='DE')) == 16
    assert len(s.get(country_code='JE')) == 0
    with pytest.raises(KeyError):
        s.get(country_code='FOOBAR')
