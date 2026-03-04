#!/usr/bin/env python3
"""Script para visualizar código TOTP em tempo real.

Uso:
    python3 scripts/totp_live.py NNWU6SZUORFWYSCWKNLEY5CLMNHWIZRZ
    python3 scripts/totp_live.py NNWU6SZUORFWYSCWKNLEY5CLMNHWIZRZ --algo sha256
    python3 scripts/totp_live.py NNWU6SZUORFWYSCWKNLEY5CLMNHWIZRZ --period 60
"""

import sys
import time

try:
    import pyotp
except ImportError:
    print("Instale pyotp: pip install pyotp")
    sys.exit(1)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="TOTP code viewer em tempo real")
    parser.add_argument("secret", help="Segredo TOTP em base32")
    parser.add_argument("--algo", default="sha1", choices=["sha1", "sha256", "sha512"])
    parser.add_argument("--digits", type=int, default=6)
    parser.add_argument("--period", type=int, default=30)
    args = parser.parse_args()

    secret = args.secret.strip().upper()
    totp = pyotp.TOTP(secret, digest=args.algo, digits=args.digits, interval=args.period)

    print(f"\n  Secret:    {secret}")
    print(f"  Algorithm: {args.algo.upper()}")
    print(f"  Digits:    {args.digits}")
    print(f"  Period:    {args.period}s")
    print(f"  {'='*40}\n")

    try:
        while True:
            code = totp.now()
            remaining = args.period - (int(time.time()) % args.period)
            bar = "█" * remaining + "░" * (args.period - remaining)
            print(f"\r  CÓDIGO: {code}   [{bar}] {remaining:2d}s  ", end="", flush=True)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n\n  Encerrado.")


if __name__ == "__main__":
    main()
