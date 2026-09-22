# Week 3 · Hands-on A — URLs you can paste into a browser

Base: `https://hapi.fhir.org/baseR4`

Every one of these is a GET. Paste it into the address bar, or append
`&_format=json` if your browser insists on rendering XML. Nothing here changes
anything on the server.

---

## Start with the contract

```
https://hapi.fhir.org/baseR4/metadata
```

The CapabilityStatement. Before writing a single query, this tells you the FHIR
version, which interactions the server allows, and which search parameters it
actually implements. Servers differ, and a parameter that is not listed will
quietly give you something you did not ask for.

**Look for:** `fhirVersion` (expect `4.0.1`), and under `rest[0].resource` the
entry for `Observation`, its `interaction` list and its `searchParam` list.

---

## One resource

```
https://hapi.fhir.org/baseR4/Patient/example
```

**Look for:** `resourceType`, `id`, `meta.versionId`, and `text.div`, the
human-readable narrative that is often the only part a clinician would recognise.

---

## A search

```
https://hapi.fhir.org/baseR4/Patient?gender=female&_count=5
```

**Look for:** you did not get five Patients. You got one Bundle, of type
`searchset`, whose `entry` array holds them. Three things to read before
anything else:

| Field | What it means |
|---|---|
| `total` | how many matched |
| `entry.length` | how many you received. **These are different numbers** |
| `link` with `relation: "next"` | there is more. Follow the URL as given |

The resources are at `entry[i].resource`, one level deeper than you expect.

---

## Narrowing it

```
https://hapi.fhir.org/baseR4/Patient?gender=female&birthdate=ge1990-01-01&_count=5
```

Prefixed comparison. `ge gt le lt eq ne`, and `ap` for approximately.

```
https://hapi.fhir.org/baseR4/Observation?code=http://loinc.org|2093-3&_count=5
```

A token with a system. The pipe separates system from value. A bare
`code=2093-3` also works and is less safe, because the same number means
different things in different code systems.

---

## Following a reference

```
https://hapi.fhir.org/baseR4/Observation?patient=example&_count=10
```

```
https://hapi.fhir.org/baseR4/Observation?patient=example&_include=Observation:patient
```

**Look for:** `_include` pulled the Patient into the same Bundle. Its entry has
`search.mode: "include"` rather than `"match"`. If you count entries without
filtering on that, your count is wrong, and it is wrong by a plausible-looking
amount, which is worse.

---

## Chaining, which is the server doing your join

```
https://hapi.fhir.org/baseR4/Observation?subject.gender=female&_count=5
```

You did not fetch the Patients. The server resolved the reference, filtered on a
field of the target, and returned only the Observations. Ask yourself what the
equivalent SQL would look like, and who would have written it.

---

## Reverse chaining

```
https://hapi.fhir.org/baseR4/Patient?_has:Observation:patient:code=http://loinc.org|2093-3
```

Patients who have such an Observation. Read it right to left.

---

## History and versions

```
https://hapi.fhir.org/baseR4/Patient/example/_history
```

Every version of that resource. Compare with the append-only discussion from
Week 2: `meta.versionId` is the same idea, enforced by the API.

---

## What to notice by the end

1. The API is the data model. Everything above is navigation of a resource graph.
2. `total` and `entry.length` are different numbers, and the first page is not
   the answer.
3. `_include` changes what is in the Bundle but not what matched.
4. The server does joins you would otherwise write yourself.
5. Some of the data on this server is excellent and some is nearly empty. It is
   a public test server, so it has the quality profile of one. Real endpoints
   vary almost as much.
