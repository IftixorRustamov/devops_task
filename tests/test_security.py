import time
import unittest

import _paths  # noqa: F401
from crystal_common.errors import UnauthorizedError
from crystal_common.security import (
    _b64encode, decode_jwt, encode_jwt, hash_password, verify_password,
)

SECRET = "s" * 40


def claims(**extra):
    now = int(time.time())
    base = {"iss": "crystal-auth", "sub": "ali", "role": "courier", "iat": now, "exp": now + 60}
    base.update(extra)
    return base


class JwtTest(unittest.TestCase):
    def test_roundtrip(self):
        token = encode_jwt(claims(), SECRET)
        self.assertEqual(decode_jwt(token, SECRET, "crystal-auth")["sub"], "ali")

    def test_rejects_bad_tokens(self):
        good = encode_jwt(claims(), SECRET)
        header, body, _signature = good.split(".")
        none_alg = _b64encode(b'{"alg":"none","typ":"JWT"}') + "." + body + "."
        cases = [
            "abc",
            encode_jwt(claims(), "boshqa-kalit" * 4),              # boshqa kalit
            encode_jwt(claims(exp=int(time.time()) - 120), SECRET),  # muddati o‘tgan
            encode_jwt(claims(iss="hacker"), SECRET),               # boshqa issuer
            encode_jwt(claims(role="superuser"), SECRET),           # noma’lum rol
            none_alg,                                               # alg=none hujumi
            header + "." + _b64encode(b'{"sub":"admin"}') + "." + _signature,  # claim almashtirilgan
        ]
        for token in cases:
            with self.assertRaises(UnauthorizedError, msg=token[:30]):
                decode_jwt(token, SECRET, "crystal-auth")


class PasswordTest(unittest.TestCase):
    def test_hash_and_verify(self):
        stored = hash_password("maxfiy-parol", iterations=1000)
        self.assertTrue(stored.startswith("pbkdf2_sha256$1000$"))
        self.assertTrue(verify_password("maxfiy-parol", stored))
        self.assertFalse(verify_password("boshqa", stored))
        self.assertNotEqual(stored, hash_password("maxfiy-parol", iterations=1000))  # tuz har xil
        self.assertFalse(verify_password("x", "buzilgan"))


if __name__ == "__main__":
    unittest.main()
