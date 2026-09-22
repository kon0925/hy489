# Week 3 — Hands-on: HL7 & FHIR

**Monday 5 and Wednesday 7 October 2026 · in class · not graded**

* **Hands-on A (Monday)** — query a live FHIR server and read what comes back.
* **Hands-on B (Wednesday)** — build a resource from a row, validate it, post it.

This is the first half of Lab 2 (Friday 16 October, graded). Everything here is
deliberately the same shape as what Lab 2 asks for, so a student who follows
along in class starts the lab with working code.

## Contents

```
week03/
├── queries.md        URLs you can paste into a browser, with what to look for
├── handson_a.py      the same calls in Python, runnable
├── handson_b.py      row -> Patient -> $validate -> conditional POST
└── requirements.txt  requests, and fhir.resources for Hands-on B
```

## Running it

```bash
pip install -r requirements.txt
python3 handson_a.py                 # read
python3 handson_b.py --dry-run       # build and validate, post nothing
python3 handson_b.py --system http://csd.uoc.gr/hy489/2026/AM1234
```

`handson_a.py` needs only `requests`. Everything is a GET, so it is safe to run
repeatedly and it writes nothing to the server.

`handson_b.py` writes. Read the ground rules below before you run it without
`--dry-run`.

## Ground rules for the public server

The default is the public HAPI test server, `https://hapi.fhir.org/baseR4`.

1. **Never post anything real.** Not your own data, not a friend's, not an
   extract from a placement. The synthetic data in `labs/lab01/data` is the only
   thing you post.
2. Everything you write is public, and anyone can delete it.
3. Always pass your own identifier namespace with `--system`, containing your
   student number. Without it you cannot find your own resources again.
4. Sequential requests with a timeout. No loops that POST a thousand resources.

If the public server is slow or down, run your own. It takes about a minute:

```bash
docker run -p 8080:8080 hapiproject/hapi:latest
python3 handson_a.py --base http://localhost:8080/fhir
```

## Where this goes

Lab 2 on 16 October is graded and starts from here. Keep whatever you write.
