# RS.ge Waybill API — Undocumented Quirks

Things the protocol PDF doesn't tell you, learned by trial and error against
`https://services.rs.ge/WayBillService/WayBillService.asmx?WSDL` on
2026-05-09.

---

## Authentication

### 1. `su` must be `<service_user_name>:<TIN>`, not just the username
The WSDL says `su: string`. The PDF examples show short usernames. In reality
the server expects the qualified form. Passing just `giooo114` returns
`STATUS=-100`. Passing `giooo114:206322102` works.

### 2. Most ops need a *service user*, not the master taxpayer login
The master creds (`tbilisi` / `123456` / TIN `206322102` in the test env) are
**only** accepted by user-management ops. The other 50+ ops require a service
user the master created via `create_service_user`. Wrong-credential calls do
not raise a SOAP fault — they silently return `STATUS=-100`.

### 3. `STATUS=-100` is "auth/authorization failed" but is NOT in `get_error_codes`
`get_error_codes` returns 145 entries; `-100` is not among them. Treat -100
as the generic rejection-because-credentials-are-wrong-for-this-op signal.

### 4. `get_error_codes` itself requires service-user creds
You cannot use master creds to look up error code names. So if your auth is
broken, you can't even read the error dictionary to debug it.

### 5. Two ops use a different parameter shape
Out of 56 ops:
- 52 use `(su, sp, ...)` — service-user creds.
- `get_service_users` uses `(user_name, user_password)` — and requires the
  *master* creds, not service-user creds. (Confusing because the field names
  are different.)
- `create_service_user` and `update_service_user` accept BOTH pairs in the
  same call (`user_name`/`user_password` for the new user, `su`/`sp` for the
  master).
- `get_server_time`, `what_is_my_ip`, `get_waybills_medicaments_moh` take no
  auth params.

### 6. `get_service_users` exposes password hints in the `NAME` field
Some entries' `NAME` text looked like a password (`123456Dx$`,
`INFinati@1`, etc.). Treat the field as untrusted free text — don't rely
on it, but be aware your customers may have leaked secrets there.

---

## UN_ID resolution

### 7. UN_ID is per-taxpayer, not per-service-user
All 98 service users under TIN `206322102` returned the same `UN_ID=731937`.
So once you know the UN_ID for a TIN you're done; you don't need to derive
it per-session.

### 8. There is no `get_un_id_from_tin` op
The WSDL has the reverse (`get_tin_from_un_id`) but no forward lookup. The
documented path to discover your own UN_ID is `get_service_users`, which
requires master creds. From a service-user-only session you have to either
hardcode UN_ID, store it at provisioning time, or have the user enter it.

---

## save_waybill validation rules (TYPE=2, transportation)

### 9. `DRIVER_TIN` is mandatory for transport-type waybills
Empty `DRIVER_TIN` returns `STATUS=-1012`. Even a populated `DRIVER_NAME`
isn't enough — the TIN is what's checked.

### 10. `CHEK_DRIVER_TIN` flips between two validators
- `CHEK_DRIVER_TIN=1` → validates as a Georgian personal ID (11 digits).
- `CHEK_DRIVER_TIN=0` → validates as a foreign-citizen ID. A Georgian-format
  11-digit number passed with `0` returns `STATUS=-1065`
  ("foreign citizen's personal ID is invalid").
- The flag is NOT a "skip validation" toggle. There's no way to bypass the
  check entirely.

### 11. `CAR_NUMBER` must match a Georgian plate format
`TEST001` returns `STATUS=-1026`. `AA001AA` (2 letters + 3 digits + 2
letters) is accepted. The exact regex isn't documented; the server enforces
it server-side.

### 12. Empty containers must still be present in the XML
`<SUB_WAYBILLS/>` and `<WOOD_DOCS_LIST/>` need to exist as empty elements
even when you have no sub-waybills or wood docs. Omitting them caused some
earlier failures (not re-tested after fix).

---

## Field-name quirks (typos baked into the live API)

You cannot fix these without breaking the contract. Match them exactly.

| What it should be    | What the API uses          |
| -------------------- | -------------------------- |
| `SELLER_UN_ID`       | `SELER_UN_ID`              |
| `TRANSPORT_COST`     | `TRANSPORT_COAST`          |
| `check_service_user` | `chek_service_user`        |
| `*_template`         | `*_tamplate` (4 ops)       |
| `send_waybill_vd`    | `send_waybil_vd` (one `l`) |

---

## PDF vs. live-WSDL divergence

### 13. The protocol PDF is partially outdated
- The PDF documents `check_service_user`. The live API has `chek_service_user`
  (typo). Calling the PDF's spelling fails with AttributeError.
- The PDF lists fewer ops than the WSDL exposes (56). Treat the WSDL as the
  source of truth.

### 14. Most `get_*` "list" ops return only `<STATUS>` on success
`get_waybill_types`, `get_waybill_units`, `get_trans_types`, `get_error_codes`
return a `<RESULT>` whose only child is `<STATUS>` containing the data — but
*also* return only `<STATUS>` on auth fail. The shape doesn't tell you which
case you're in. Inspect the STATUS value, not the presence of children.

---

## Safe minimal waybill recipe (works as of 2026-05-09)

```
TYPE=2  (delivery with transportation)
STATUS=0  (saved, not yet activated)
SELER_UN_ID=<from TIN lookup>
BUYER_TIN=<11 digits>, CHEK_BUYER_TIN=0  (test buyer 12345678910 works)
DRIVER_TIN=<11 digits Georgian>, CHEK_DRIVER_TIN=1
CAR_NUMBER=<Georgian plate format, e.g. AA001AA>
BEGIN_DATE=<future ISO datetime>
TRANS_ID=1  (truck)
TRAN_COST_PAYER=1  (buyer pays)
GOODS_LIST/GOODS: ID=0, UNIT_ID=1, STATUS=1, VAT_TYPE=0, BAR_CODE=anything
SUB_WAYBILLS and WOOD_DOCS_LIST present but empty
```

This combination produced waybill ID 1017728320 successfully.

---

## Operational notes

### 15. Cache `get_error_codes` — messages are in Georgian only
145 entries, all `TEXT` fields are Georgian. You'll want a translation layer
before showing these to non-Georgian-speaking users. Cache the dictionary;
it doesn't change frequently.

### 16. SOAP namespace oddity
`save_waybill` returns a `<RESULT>` with `xmlns=""` plus the standard SOAP
namespaces redeclared. Parsers that strictly enforce namespaces may need
configuration to handle the empty default namespace.
