## 0.0.8 (2019-10-17)
* Python 3.8 support
* Dropped support for Python 2.7, 3.4

## 0.0.7 (2014-09-20)
* Renamed module: `good.validators._base` -> `good.validators.base`
* PyPy: fixed slight incompatibilities with PyPy
* Error-passthrough for iterable schemas of a single member: [issue #2](https://github.com/kolypto/py-good/issues/2)
* Changed `Length()` error message so it's acceptable for both lists and strings

## 0.0.6 (2014-09-07)

* New validators: `Test`, `Date`, `Time`, `DateTime`
* `Map` supports `in` checks and now works with `In`: [details](README.md#map)
* Unit-testing with tox
* Added changelog :)

## 0.0.5 (2014-09-05)

* Type support for Python 3.4. enums
* New validator: `Map`
