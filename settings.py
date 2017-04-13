import os
from os import environ

import dj_database_url
#from otree.api import Currency as c, currency_range
#from boto.mturk import qualification

import otree.settings

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# the environment variable OTREE_PRODUCTION controls whether Django runs in
# DEBUG mode. If OTREE_PRODUCTION==1, then DEBUG=False
if environ.get('OTREE_PRODUCTION') not in {None, '', '0'}:
    DEBUG = False
else:
    DEBUG = True
#OTREE_PRODUCTION = 1
#DEBUG = False
ADMIN_USERNAME = 'admin'

# for security, best to set admin password in an environment variable
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')
# don't share this with anybody.
SECRET_KEY = 'l)2(&wh@^_l9@e04v20f#ne-*hw_z!94dz(igf$_m^ifu3g4mp'

# To use a database other than sqlite,
# set the DATABASE_URL environment variable.
# Examples:
# postgres://USER:PASSWORD@HOST:PORT/NAME
# mysql://USER:PASSWORD@HOST:PORT/NAME

DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///' + os.path.join(BASE_DIR, 'db.sqlite3')
    )
}

# AUTH_LEVEL:
# If you are launching a study and want visitors to only be able to
# play your app if you provided them with a start link, set the
# environment variable OTREE_AUTH_LEVEL to STUDY.
# If you would like to put your site online in public demo mode where
# anybody can play a demo version of your game, set OTREE_AUTH_LEVEL
# to DEMO. This will allow people to play in demo mode, but not access
# the full admin interface.

AUTH_LEVEL = environ.get('OTREE_AUTH_LEVEL')
AUTH_LEVEL = 'STUDY'
# setting for integration with AWS Mturk
AWS_ACCESS_KEY_ID = environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = environ.get('AWS_SECRET_ACCESS_KEY')


# e.g. EUR, CAD, GBP, CHF, CNY, JPY
REAL_WORLD_CURRENCY_CODE = 'USD'
USE_POINTS = False


LANGUAGE_CODE = 'en'

# if an app is included in SESSION_CONFIGS, you don't need to list it here
INSTALLED_APPS = ['otree']

# SENTRY_DSN = ''

DEMO_PAGE_INTRO_TEXT = """
oTree: Permit Experiments
"""

#ROOM_DEFAULTS = {}

#ROOMS = [
#    {
#        'name': 'Permit_Auctions',
#        'display_name': 'Permit Markets',
#        'participant_label_file': '/Users/wms5f/Programming/permitauctionapp/Permit_Auctions.txt',
#        'use_secure_urls': True,
#    },
#]



SESSION_CONFIG_DEFAULTS = {
    'real_world_currency_per_point': 0.000,
    'participation_fee': 0.00,
    'doc': "",
}


SESSION_CONFIGS = [
     {
    'name': 'Permit_Auctions',
    'display_name': 'Permit Markets',
    'num_demo_participants': 12,
    'app_sequence': ['permitauctions'],
    'random_start_order': True,
    'permits_persist': True,
    'initial_cap': 42,
    'cap_decrement': 1,
    'initial_ecr_reserve_amount': 6,
    'ecr_trigger_price': 8,
    'ecr_reserve_increment': 2,
    'num_low_emitters': 6,
    'supply_step': False,
    'num_high_emitters': 6,
    'random_seed': 113,
    'output_price_random_seed': 1288,
    'show_instructions': False,
    'last_round': 30,
    'low_emitter_min_cost': 10,
    'low_emitter_max_cost': 30,
    'high_emitter_min_cost': 1,
    'high_emitter_max_cost': 30,
    'low_output_price': 30,
    'high_output_price_increment': 10,
    'payout_rate': 0.05,
    'price_containment_trigger': 12,
    'price_containment_reserve_amount': 8 # Max permits to add if price over containment trigger
     }
]

# anything you put after the below line will override
# oTree's default settings. Use with caution.
otree.settings.augment_settings(globals())
