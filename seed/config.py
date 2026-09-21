"""Validated shared configuration; no web dependency in the core."""
import math

DEFAULTS = {
    'name':'SEED', 'port':8765, 'theme':'system', 'refresh_seconds':5,
    'observe_interval':8, 'reflect_interval':12, 'rest_interval':35,
    'epsilon':.15, 'alpha':.18, 'memory_budget':2*1024**3,
    'log_bytes':5*1024**2, 'log_count':3, 'backup_retention':7,
    'prediction_error_curiosity':False, 'advanced_concept_inference':False,
}
RANGES = {'port':(1024,65535), 'refresh_seconds':(2,60), 'observe_interval':(8,3600),
          'reflect_interval':(12,3600), 'rest_interval':(35,3600), 'epsilon':(0,1), 'alpha':(0,1),
          'memory_budget':(64*1024**2,64*1024**3), 'log_bytes':(1024**2,100*1024**2),
          'log_count':(1,10), 'backup_retention':(1,100)}


def validate_settings(data: dict) -> dict:
    if not isinstance(data, dict) or data.keys() - DEFAULTS.keys():
        raise ValueError('Unknown setting')
    result = dict(data)
    for key, value in result.items():
        if key in RANGES:
            low, high = RANGES[key]
            if type(value) not in (int,float) or not math.isfinite(value) or not low <= value <= high:
                raise ValueError(f'{key} must be between {low} and {high}')
            if key not in ('epsilon','alpha') and type(value) is not int:
                raise ValueError(f'{key} must be an integer')
            if key == 'alpha' and value == 0:
                raise ValueError('alpha must be greater than zero')
        elif key == 'name':
            if not isinstance(value, str) or not 1 <= len(value.strip()) <= 64:
                raise ValueError('Name must contain 1–64 characters')
            result[key] = value.strip()
        elif key == 'theme':
            if value not in ('system','dark','light'):
                raise ValueError('Unknown theme')
        elif value is not False:
            raise ValueError('This experimental capability is not implemented and must stay off')
    return result
