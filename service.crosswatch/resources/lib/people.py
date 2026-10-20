# SPDX-License-Identifier: GPL-2.0-only
"""Viewers and the people CrossWatch lists (docs/contract.md, People).

A viewer linked to a person keeps that person's id and carries the person's exact name, taken
over at the link and again whenever it changes, because the profile name is what CrossWatch
routes on. Pure, so the service and the
settings script share it without either importing the other.
"""

import unicodedata
from collections.abc import Collection, Sequence
from dataclasses import dataclass, replace

from resources.lib.models import Viewer
from resources.lib.routes import Person


def _folded(name: str) -> str:
    return unicodedata.normalize("NFC", unicodedata.normalize("NFC", name).casefold())


def crosswatch_name(name: str) -> str:
    """The name as CrossWatch compares it loosely (normalize_media_account_name in CrossWatch's
    cw_platform/account_match.py): case folded, invisible format characters dropped, and only
    letters and digits kept, each with the marks attached to it. An accent therefore counts, so
    "José" is not "Jose", and a name in any script has a key.
    """
    visible = "".join(ch for ch in name if unicodedata.category(ch) != "Cf")
    out: list[str] = []
    attached = False
    for ch in _folded(visible):
        kind = unicodedata.category(ch)[0]
        if kind in "LN":
            out.append(ch)
            attached = True
        elif kind == "M" and attached:
            out.append(ch)
        else:
            attached = False
    return "".join(out)


def exact_name(name: str) -> str:
    """The form CrossWatch compares where the loose key is empty or ambiguous
    (exact_media_account_name)."""
    return _folded(name).strip()


def same_name(a: str, b: str) -> bool:
    """Whether CrossWatch reads the two names as one (media_account_names_match)."""
    loose = crosswatch_name(a)
    if loose:
        return loose == crosswatch_name(b)
    exact = exact_name(a)
    return bool(exact) and exact == exact_name(b)


def _accepts(person: Person, name: str, people: Sequence[Person]) -> bool:
    """Whether CrossWatch routes name to this person (route_profile_accepts in CrossWatch's
    providers/scrobble/routes.py)."""
    wanted = exact_name(name)
    exact = exact_name(person.name)
    if not wanted or not exact:
        return False
    if sum(1 for p in people if exact_name(p.name) == exact) > 1:
        return False
    loose = crosswatch_name(person.name)
    if not loose or sum(1 for p in people if crosswatch_name(p.name) == loose) > 1:
        return wanted == exact
    return crosswatch_name(name) == loose


def match_person(name: str, people: Sequence[Person], taken: Collection[str]) -> Person | None:
    """The person a viewer name links to, as CrossWatch would route it.

    CrossWatch compares loosely, except between two profiles that differ only in spaces or
    punctuation: each of those takes only its own spelling, apart from case. Two profiles with
    the same exact name take nobody. A name with no letter or digit compares by its exact form,
    so it is not linked to every other such name.

    Judged over all people, taken included: a person already linked still makes its loose twin
    ambiguous, as it does for CrossWatch.
    """
    person = next((p for p in people if _accepts(p, name, people)), None)
    return None if person is None or person.id in taken else person


@dataclass(frozen=True)
class Reconciled:
    viewers: list[Viewer]
    renamed: tuple[tuple[str, str], ...]
    linked: int
    skipped: int

    @property
    def changed(self) -> bool:
        return bool(self.renamed or self.linked)


def _clashes(viewers: Sequence[Viewer], index: int, name: str) -> bool:
    """A second viewer under the same name would merge two people's playlists and answers."""
    return any(v.name.casefold() == name.casefold() for i, v in enumerate(viewers) if i != index)


def reconcile(viewers: Sequence[Viewer], people: Sequence[Person]) -> Reconciled:
    """Rename linked viewers to their person's current name, then link the rest.

    A viewer linked on a loose match is renamed to the person's spelling in the same pass, and
    reported in renamed like any other rename, so remembered answers and kept watches follow.
    A rename that would clash with another viewer is skipped, link included.
    """
    by_id = {p.id: p for p in people}
    out = list(viewers)
    renamed: list[tuple[str, str]] = []
    skipped = 0
    for index, viewer in enumerate(out):
        person = by_id.get(viewer.person_id or "")
        if person is None or person.name == viewer.name:
            continue
        if _clashes(out, index, person.name):
            skipped += 1
            continue
        renamed.append((viewer.name, person.name))
        out[index] = replace(viewer, name=person.name)
    linked = 0
    taken = {v.person_id for v in out if v.person_id}
    for index, viewer in enumerate(out):
        if viewer.person_id:
            continue
        person = match_person(viewer.name, people, taken)
        if person is None:
            continue
        if person.name != viewer.name:
            if _clashes(out, index, person.name):
                skipped += 1
                continue
            renamed.append((viewer.name, person.name))
        out[index] = replace(viewer, name=person.name, person_id=person.id)
        taken.add(person.id)
        linked += 1
    return Reconciled(out, tuple(renamed), linked, skipped)
