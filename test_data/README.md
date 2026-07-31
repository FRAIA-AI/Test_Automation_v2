# Required private test fixtures

Copy these two existing synthetic fixtures from the original monitoring repository:

```text
test-audio.webm
  -> test_data/consultation-audio.webm

test_data/2024-12-14_CGM_P300_1_Ref.FNX
  -> test_data/2024-12-14_CGM_P300_1_Ref.FNX
```

The binary files are not reproduced by this scaffold because they were not available in the local workspace.

The JSON oracle files are committed. Before trusting the deep tests:

1. Update `consultation-audio.oracle.json` with distinctive words actually spoken in the WebM fixture and expected in its generated note.
2. Review `fnx.oracle.json` against the known synthetic FNX record.
3. Keep every fixture synthetic or properly anonymized.
