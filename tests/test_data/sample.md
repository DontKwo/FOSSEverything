# Mission Specification

A *GitHub Flavored Markdown* sample with **bold**, ~~strikethrough~~, and a [link](https://example.com).

## Checklist

- [x] Pre-launch check
- [x] Fuel loading
- [ ] Ignition
- [ ] Liftoff

## Code

```python
def calc_dv(isp: float, m0: float, mf: float, g0: float = 9.80665) -> float:
    return isp * g0 * math.log(m0 / mf)
```

## Stage Table

| Stage | Velocity (m/s) | Status  |
|-------|---------------:|:--------|
| 1     |         1250.5 | nominal |
| 2     |         4800.0 | nominal |
| 3     |         7800.0 | pending |

> Note: all values are illustrative.
