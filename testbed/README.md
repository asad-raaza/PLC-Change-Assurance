# Testbed

```
engineering / attack client  →  assurance API / Modbus adapter  →  water-tank simulator
```

The in-process simulator is the reproducible default. A future OpenPLC container can share the same register map (`backend/app/adapters/modbus.py`).

Do not attach this compose file to a plant network.
