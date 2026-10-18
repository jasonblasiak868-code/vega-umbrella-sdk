"""Shared helpers for the umbrella tests (not a test file)."""
import pathlib
import tempfile
import types

from vega_jacket.humanauth import human_signer
from vega_umbrella.organism import Organism

PW, DEV, SURF = "correct horse battery", "dev-umb", "surf-umb"


def build():
    blob, pub = human_signer.generate(PW)
    t = pathlib.Path(tempfile.mkdtemp())
    org = Organism(str(t / "home"), pub, DEV, SURF)

    def sign(action, params, lease=300):
        return human_signer.sign(blob, PW, DEV, SURF, action, params, lease)
    other_blob, other_pub = human_signer.generate(PW)

    def sign_other(action, params, lease=300):
        return human_signer.sign(other_blob, PW, DEV, SURF, action, params, lease)
    return types.SimpleNamespace(org=org, t=t, sign=sign, sign_other=sign_other, pub=pub)
