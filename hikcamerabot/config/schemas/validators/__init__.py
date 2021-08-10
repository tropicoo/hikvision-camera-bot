from marshmallow import (
    validate as v,
)

non_empty_str = v.Length(min=1)
int_min_1 = v.Range(min=1)
